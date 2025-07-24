"""Utilidades para procesar resultados de transcripción del Media Stream de Twilio."""

import json
import time
from fastapi import WebSocket

from .supabase import save_transcript # Asumiendo que esta función es para guardar transcripciones
from .tts import speak # Importamos speak para poder generar audio de respuesta


async def process_stream(ws: WebSocket, call_id: str) -> None:
    """
    Procesa mensajes por WebSocket desde Twilio, esperando eventos
    de reconocimiento de voz (speech_recognition_result).
    """
    print(f"[{call_id}] Starting Twilio native STT stream processing.")

    try:
        # Bucle para recibir mensajes continuamente del WebSocket
        while True:
            message = await ws.receive()

            if "text" in message:
                try:
                    control_data = json.loads(message["text"])
                    event = control_data.get("event")

                    # Evento clave: Twilio envía la transcripción aquí
                    if event == "speech_recognition_result":
                        recognition = control_data.get("recognition", {})
                        # El primer elemento de 'alternative' es la mejor transcripción
                        transcript_info = recognition.get("alternative", [{}])[0]
                        transcript = transcript_info.get("transcript", "").strip() # Limpiamos espacios en blanco
                        confidence = transcript_info.get("confidence")
                        is_final = recognition.get("isFinal", False)
                        speech_event_type = recognition.get("speechEventType") # 'partial_result' o 'end_of_utterance'

                        if transcript: # Solo procesamos si hay texto en la transcripción
                            transcription_status = "Final" if is_final else "Parcial"
                            print(
                                f"[{call_id}] {transcription_status} Transcripción "
                                f"(Conf: {confidence:.2f}, Tipo: {speech_event_type}): '{transcript}'"
                            )

                            # Cuando la transcripción es final, la enviamos al LLM
                            if is_final:
                                # Guarda la transcripción final en tu base de datos
                                # Puedes ajustar los timestamps si tu save_transcript los usa de forma diferente
                                await save_transcript(call_id, time.time(), time.time(), transcript)
                                print(f"[{call_id}] Enviando a LLM el texto final: '{transcript}'")

                                # --- LÓGICA DE TU AGENTE DE IA ---
                                # 1. Envía el 'transcript' final a tu LLM
                                # Por ejemplo:
                                # llm_response_text = await get_llm_response(call_id, transcript) # Necesitarás implementar esto
                                llm_response_text = f"Has dicho: '{transcript}'. Gracias por tu mensaje." # Placeholder

                                if llm_response_text:
                                    # 2. Genera el audio TTS de la respuesta del LLM
                                    response_audio_url = await speak(llm_response_text)

                                    if response_audio_url:
                                        # 3. Envía un comando a Twilio para reproducir el audio.
                                        # Esto se hace enviando un mensaje JSON al WebSocket
                                        # con una acción de "play" o "say".
                                        # Twilio espera un TwiML dentro de un objeto 'media' para reproducirlo.
                                        play_twiml = f"<Play>{response_audio_url}</Play>"
                                        await ws.send_json({
                                            "event": "media",
                                            "media": {
                                                "payload": play_twiml
                                            }
                                        })
                                        print(f"[{call_id}] Enviado TwiML de respuesta a Twilio.")
                                    else:
                                        print(f"[{call_id}] No se pudo generar audio para la respuesta del LLM.")
                                else:
                                    print(f"[{call_id}] LLM no generó respuesta para: '{transcript}'")

                    elif event == "media":
                        # Estos son los chunks de audio raw. Con 'track="inbound_speech"',
                        # Twilio ya nos envía la transcripción, así que podemos ignorar estos chunks
                        # a menos que los necesitemos para otra cosa (ej. grabar la llamada).
                        pass

                    elif event == "stop":
                        # Twilio envía este evento cuando la conexión del stream se cierra.
                        print(f"[{call_id}] Twilio Media Stream 'stop' event received. Closing WebSocket.")
                        break # Salir del bucle, cerrando el WebSocket

                    elif event == "start":
                        # Este es el evento de inicio de stream, ya manejado en main.py.
                        pass

                    else:
                        print(
                            f"[{call_id}] Received unhandled control message event: {event} -> "
                            f"{json.dumps(control_data, indent=2)}"
                        )

                except json.JSONDecodeError:
                    print(f"[{call_id}] Received non-JSON text message: {message['text']}")

            # Manejo de desconexión del WebSocket
            elif message is None or message["type"] == "websocket.disconnect":
                print(f"[{call_id}] WebSocket disconnected by client.")
                break

            else:
                print(f"[{call_id}] Received unexpected message type: {message.get('type')}")

    except Exception as e:
        print(f"[{call_id}] Error processing stream: {e}")
    finally:
        print(f"[{call_id}] STT stream processing finished.")
