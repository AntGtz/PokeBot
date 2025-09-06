import json
import boto3
import os
import requests

# --- Clientes de AWS ---
bedrock_runtime = boto3.client("bedrock-runtime")
secrets_manager = boto3.client("secretsmanager")

# --- Variables Globales ---
# Cacheamos el token para no tener que buscarlo en cada invocación
TELEGRAM_BOT_TOKEN = None

def get_telegram_token():
    """Obtiene el token del bot de Telegram desde AWS Secrets Manager."""
    global TELEGRAM_BOT_TOKEN
    if TELEGRAM_BOT_TOKEN:
        return TELEGRAM_BOT_TOKEN

    secret_arn = os.environ.get("TELEGRAM_SECRET_ARN")
    if not secret_arn:
        raise ValueError("La variable de entorno TELEGRAM_SECRET_ARN no está configurada.")
    
    print(f"Buscando secreto con ARN: {secret_arn}")
    response = secrets_manager.get_secret_value(SecretId=secret_arn)
    secret_data = json.loads(response['SecretString'])
    TELEGRAM_BOT_TOKEN = secret_data['TELEGRAM_BOT_TOKEN']
    return TELEGRAM_BOT_TOKEN

def call_telegram_api(method, payload):
    """Función helper para llamar a la API de Telegram."""
    try:
        token = get_telegram_token()
        url = f"https://api.telegram.org/bot{token}/{method}"
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"Respuesta de la API de Telegram: {response.json()}")
    except Exception as e:
        print(f"Error al llamar a la API de Telegram: {e}")

def get_pokemon_info(pokemon_name):
    """Obtiene datos de la PokeAPI y genera un resumen con Bedrock."""
    # 1. Obtener datos de la PokeAPI
    poke_api_url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
    poke_response = requests.get(poke_api_url)
    poke_response.raise_for_status()
    pokemon_data = poke_response.json()

    # 2. Simplificar datos y extraer imagen
    image_url = pokemon_data.get("sprites", {}).get("front_default")
    filtered_data = {
        "name": pokemon_data.get("name"),
        "types": [t["type"]["name"] for t in pokemon_data.get("types", [])],
        "abilities": [a["ability"]["name"] for a in pokemon_data.get("abilities", [])],
    }

    # 3. Crear prompt para Bedrock
    prompt = f"""Eres un experto de la Pokédex. Con los siguientes datos de un Pokémon: {json.dumps(filtered_data)}.
    Crea un resumen amigable y conciso (máximo 3 frases) como si fueras una entrada de la Pokédex."""
    
    # 4. Invocar a Bedrock
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    body_to_bedrock = json.dumps({
        "anthropic_version": "bedrock-2023-05-31", "max_tokens": 200, "messages": messages
    })
    response = bedrock_runtime.invoke_model(modelId=model_id, body=body_to_bedrock)
    response_body = json.loads(response.get("body").read())
    ai_response = response_body['content'][0]['text']
    
    return image_url, ai_response

def lambda_handler(event, context):
    print(f"Evento recibido: {json.dumps(event)}")
    path = event.get("requestContext", {}).get("http", {}).get("path")
    body = json.loads(event.get("body", "{}"))

    # --- RUTA PARA TELEGRAM ---
    if path == "/telegram":
        message = body.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        pokemon_name = message.get("text")

        if not chat_id or not pokemon_name:
            return {"statusCode": 200} 

        try:
            image_url, pokedex_entry = get_pokemon_info(pokemon_name)
            
            # Enviar la foto
            if image_url:
                call_telegram_api("sendPhoto", {"chat_id": chat_id, "photo": image_url})
            
            # Enviar la descripción
            call_telegram_api("sendMessage", {"chat_id": chat_id, "text": pokedex_entry})

        except requests.exceptions.HTTPError as e:
            error_message = f"¡Lo siento! No encontré a '{pokemon_name}' en la Pokédex." if e.response.status_code == 404 else "Hubo un problema con la PokeAPI."
            call_telegram_api("sendMessage", {"chat_id": chat_id, "text": error_message})
        except Exception as e:
            print(f"Error inesperado: {e}")
            call_telegram_api("sendMessage", {"chat_id": chat_id, "text": "¡Uy! Algo salió mal. Inténtalo de nuevo."})
        
        return {"statusCode": 200}

    # --- RUTA PARA LA API PÚBLICA ORIGINAL ---
    elif path == "/pokemon":
        pokemon_name = body.get("pokemon_name")
        if not pokemon_name:
            return {"statusCode": 400, "body": json.dumps({"error": "El campo 'pokemon_name' es requerido."})}
        try:
            _, pokedex_entry = get_pokemon_info(pokemon_name)
            return {"statusCode": 200, "body": json.dumps({"pokedex_entry": pokedex_entry})}
        except Exception as e:
            return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
            
    return {"statusCode": 404, "body": "Ruta no encontrada."}

