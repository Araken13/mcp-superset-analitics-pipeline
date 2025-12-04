"""
Produtor de eventos de teste para Kafka
Gera eventos aleatórios para testar o pipeline
"""
import json
import time
import random
import uuid
from datetime import datetime
from kafka import KafkaProducer

# Configurações
KAFKA_BOOTSTRAP_SERVERS = ['localhost:29092']
KAFKA_TOPIC = 'eventos'

# Dados de exemplo
USUARIOS = ['usuario1', 'usuario2', 'usuario3', 'usuario4', 'usuario5']
EVENTOS = ['login', 'logout', 'compra', 'visualizacao', 'clique', 'cadastro']
CATEGORIAS = ['ecommerce', 'navegacao', 'autenticacao', 'interacao']

def criar_produtor():
    """Cria o produtor Kafka"""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8') if k else None
    )

def gerar_evento():
    """Gera um evento aleatório"""
    return {
        'id': str(uuid.uuid4()),
        'usuario': random.choice(USUARIOS),
        'evento': random.choice(EVENTOS),
        'valor': round(random.uniform(10.0, 1000.0), 2),
        'timestamp': datetime.now().isoformat(),
        'categoria': random.choice(CATEGORIAS)
    }

def main():
    """Função principal"""
    print("🚀 Iniciando produtor de eventos...")
    print(f"📤 Enviando para: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"📋 Tópico: {KAFKA_TOPIC}")
    print("⏸️  Pressione Ctrl+C para parar\n")
    
    producer = criar_produtor()
    contador = 0
    
    try:
        while True:
            # Gerar evento
            evento = gerar_evento()
            
            # Enviar para Kafka
            future = producer.send(
                KAFKA_TOPIC,
                key=evento['id'],
                value=evento
            )
            
            # Confirmar envio
            future.get(timeout=10)
            
            contador += 1
            print(f"✅ Evento {contador} enviado: {evento['evento']} - "
                  f"{evento['usuario']} - R$ {evento['valor']:.2f}")
            
            # Aguardar antes de enviar próximo evento
            time.sleep(random.uniform(0.5, 2.0))
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Produtor interrompido. Total de eventos enviados: {contador}")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
    finally:
        producer.close()

if __name__ == "__main__":
    main()
