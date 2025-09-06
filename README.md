Taller Completo: Crea un Experto en Pokémon con IA en AWS y Chatea con él en Telegram¡Bienvenido! En este taller práctico, construiremos y desplegaremos una aplicación serverless completa. Al final, tendrás un bot de Telegram funcional que utiliza IA generativa para darte información sobre cualquier Pokémon.Usaremos AWS CloudShell, por lo que no necesitas instalar nada en tu computadora.⚠️ Prerrequisitos MUY IMPORTANTESTener una cuenta de AWS activa.Habilitar el acceso a los modelos de Bedrock:Ve a la Consola de Amazon Bedrock.En el menú de la izquierda, ve a Model access > Manage model access y solicita acceso para Anthropic / Claude. La aprobación puede tardar unos minutos. No podrás completar el taller si no haces esto.Tener una cuenta de Telegram.Parte 1: Crear el Bot y Guardar el Token de Forma SeguraAntes de escribir código, necesitamos obtener la "llave" de nuestro bot de Telegram y guardarla de forma segura.Paso 1: Crear tu Bot en TelegramAbre Telegram (en tu teléfono o en la app de escritorio).Busca el contacto @BotFather (es el bot oficial para crear otros bots) y empieza una conversación con él.Escribe el comando /newbot.BotFather te pedirá un nombre para tu bot (ej. Poke Asistente IA) y luego un nombre de usuario único que debe terminar en bot (ej. MiPokeAsistenteIABot).¡Éxito! BotFather te dará un Token de API. Se ve algo como 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11. Copia y guarda este token. Es crucial para los siguientes pasos.Paso 2: Guardar el Token en AWS Secrets ManagerNunca debemos poner secretos (como un token) directamente en el código.Ve a la Consola de AWS Secrets Manager.Haz clic en Store a new secret.Selecciona Other type of secret.En la sección Key/value pairs, en el primer campo (Key), escribe TELEGRAM_BOT_TOKEN. En el campo de al lado (Value), pega el token que te dio BotFather.Deja la encriptación por defecto y haz clic en Next.Dale un nombre al secreto, por ejemplo, TelegramBotTokenForPokeApp, y una descripción. Haz clic en Next.En la siguiente página, puedes dejar todo como está. Haz clic en Next.Revisa todo y haz clic en Store.Una vez creado, entra en los detalles del secreto y copia su ARN. Lo necesitaremos durante el despliegue.Parte 2: Construir y Desplegar la Aplicación ServerlessAhora que tenemos nuestro secreto guardado, ¡es hora de construir la aplicación!Paso 3: Iniciar el Entorno y el ProyectoInicia sesión en tu Consola de AWS.En la barra de navegación superior, haz clic en el ícono de CloudShell (>_). Espera un minuto a que tu terminal esté lista.En la terminal de CloudShell, ejecuta sam init para crear un nuevo proyecto:sam init
Selecciona las siguientes opciones:1 - AWS Quick Start Templates1 - Hello World Examplepython3.11Project name: poke-chatbot-samPaso 4: Configurar la Infraestructura (template.yaml)Navega a la nueva carpeta: cd poke-chatbot-samAbre el archivo template.yaml con un editor de texto (nano es el más sencillo): nano template.yamlBorra todo el contenido y pégale el siguiente código. Este archivo define todos los recursos de AWS que necesitamos.AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Taller de Poke-Chatbot con Bedrock, SAM y Telegram.

Parameters:
  TelegramSecretArn:
    Type: String
    Description: El ARN del secreto en AWS Secrets Manager que contiene el token del bot de Telegram.

Resources:
  ChatbotFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: app.lambda_handler
      Runtime: python3.11
      Timeout: 60
      MemorySize: 512
      Environment:
        Variables:
          TELEGRAM_SECRET_ARN: !Ref TelegramSecretArn
      Events:
        TelegramWebhook:
          Type: Api
          Properties:
            Path: /telegram
            Method: post
      Policies:
        - Statement:
          - Effect: Allow
            Action:
              - bedrock:InvokeModel
            Resource: "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
        - Statement:
          - Effect: Allow
            Action:
              - secretsmanager:GetSecretValue
            Resource: !Ref TelegramSecretArn

Outputs:
  ChatbotApiEndpoint:
    Description: "URL de la API para el webhook de Telegram"
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}[.amazonaws.com/Prod](https://.amazonaws.com/Prod)"
Guarda y cierra el archivo (en nano, es Ctrl+X, luego Y, y Enter).Paso 5: Añadir Dependencias (requirements.txt)Nuestra función necesita la librería requests para hablar con las APIs externas.Abre el archivo de dependencias: nano src/requirements.txtAñade la siguiente línea, luego guarda y cierra:requests
Paso 6: Escribir la Lógica del Bot (app.py)Esta es la parte central de nuestro bot, donde ocurre toda la magia.Abre el archivo principal de la lógica: nano src/app.pyBorra todo el contenido y pégale este nuevo código Python:import json
import boto3
import os
import requests

bedrock_runtime = boto3.client("bedrock-runtime")
secrets_manager = boto3.client("secretsmanager")
TELEGRAM_BOT_TOKEN = None

def get_telegram_token():
    global TELEGRAM_BOT_TOKEN
    if TELEGRAM_BOT_TOKEN:
        return TELEGRAM_BOT_TOKEN
    secret_arn = os.environ.get("TELEGRAM_SECRET_ARN")
    response = secrets_manager.get_secret_value(SecretId=secret_arn)
    secret_data = json.loads(response['SecretString'])
    TELEGRAM_BOT_TOKEN = secret_data['TELEGRAM_BOT_TOKEN']
    return TELEGRAM_BOT_TOKEN

def call_telegram_api(method, payload):
    try:
        token = get_telegram_token()
        url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){token}/{method}"
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error al llamar a la API de Telegram: {e}")

def get_pokemon_info(pokemon_name):
    poke_api_url = f"[https://pokeapi.co/api/v2/pokemon/](https://pokeapi.co/api/v2/pokemon/){pokemon_name.lower()}"
    poke_response = requests.get(poke_api_url)
    poke_response.raise_for_status()
    pokemon_data = poke_response.json()

    image_url = pokemon_data.get("sprites", {}).get("front_default")
    filtered_data = {
        "name": pokemon_data.get("name"),
        "types": [t["type"]["name"] for t in pokemon_data.get("types", [])],
        "abilities": [a["ability"]["name"] for a in pokemon_data.get("abilities", [])],
    }

    prompt = f"""Eres un experto de la Pokédex. Con los siguientes datos de un Pokémon: {json.dumps(filtered_data)}.
    Crea un resumen amigable y conciso (máximo 3 frases) como si fueras una entrada de la Pokédex."""

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
    body = json.loads(event.get("body", "{}"))
    message = body.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    pokemon_name = message.get("text")

    if not chat_id or not pokemon_name:
        return {"statusCode": 200} 

    try:
        image_url, pokedex_entry = get_pokemon_info(pokemon_name)
        if image_url:
            call_telegram_api("sendPhoto", {"chat_id": chat_id, "photo": image_url})
        call_telegram_api("sendMessage", {"chat_id": chat_id, "text": pokedex_entry})
    except requests.exceptions.HTTPError as e:
        error_message = f"¡Lo siento! No encontré a '{pokemon_name}' en la Pokédex." if e.response.status_code == 404 else "Hubo un problema con la PokeAPI."
        call_telegram_api("sendMessage", {"chat_id": chat_id, "text": error_message})
    except Exception as e:
        call_telegram_api("sendMessage", {"chat_id": chat_id, "text": "¡Uy! Algo salió mal. Inténtalo de nuevo."})

    return {"statusCode": 200}
Guarda y cierra el archivo.Paso 7: Desplegar en la NubeConstruye la aplicación. Usamos --use-container para que SAM instale las dependencias en un entorno limpio de Docker.sam build --use-container
Despliega los cambios:sam deploy --guided
SAM te hará algunas preguntas:Stack Name [sam-app]: Escribe poke-chatbot-tallerAWS Region: Asegúrate que sea la región donde tienes Bedrock habilitado (ej. us-east-1).Parameter TelegramSecretArn: Pega aquí el ARN del secreto que copiaste en el Paso 2.Confirm changes before deploy [y/N]: Escribe yAllow SAM CLI IAM role creation [Y/n]: Escribe yPara el resto, puedes aceptar los valores por defecto.Parte 3: Configurar y ProbarPaso 8: Configurar el WebhookNecesitamos decirle a Telegram a dónde debe enviar los mensajes que recibe tu bot.Al terminar el despliegue de SAM, copia la URL de la API de los Outputs. Se verá algo como https://xxxxx.execute-api.us-east-1.amazonaws.com/Prod.Construye la siguiente URL en un editor de texto, reemplazando <TU_TOKEN> y <URL_DE_TU_API> con tus valores:https://api.telegram.org/bot<TU_TOKEN>/setWebhook?url=<URL_DE_TU_API>/telegramPega esa URL completa en tu navegador y presiona Enter. Deberías ver: {"ok":true,"result":true,"description":"Webhook was set"}.¡A Probar!Abre la conversación con tu bot en Telegram y envíale el nombre de un Pokémon. ¡Debería responderte con su foto y una descripción generada por IA!Parte 4: Limpieza¡Importante! Para evitar costos inesperados, elimina todos los recursos creados ejecutando este comando en CloudShell:aws cloudformation delete-stack --stack-name poke-chatbot-taller
