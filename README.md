# DogeDictate v1.0.0

DogeDictate é uma ferramenta de ditado por voz que permite converter fala em texto em tempo real, com suporte a múltiplos idiomas e serviços de reconhecimento de fala.

## Recursos

- Reconhecimento de fala em tempo real
- Suporte a múltiplos idiomas
- Integração com Azure Speech Services, OpenAI Whisper e Google Speech-to-Text
- Tradução automática entre idiomas
- Barra flutuante para controle rápido
- Atalhos de teclado personalizáveis
- Interface moderna e intuitiva

## Requisitos do Sistema

- Windows 10/11, macOS 10.14+ ou Linux
- Python 3.8 ou superior
- Microfone funcional
- Conexão com a internet (para serviços de reconhecimento de fala baseados em nuvem)

## Instalação

1. Clone o repositório:
   ```
   git clone https://github.com/seu-usuario/DogeDictate.git
   cd DogeDictate
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Execute o aplicativo:
   ```
   python run.py
   ```

## Configuração

Na primeira execução, o DogeDictate irá criar um arquivo de configuração padrão. Você pode personalizar as configurações através da interface do aplicativo.

### Serviços de Reconhecimento de Fala

O DogeDictate suporta os seguintes serviços:

- **Azure Speech Services**: Requer uma chave de API e região
- **OpenAI Whisper**: Requer uma chave de API
- **Google Speech-to-Text**: Requer um arquivo de credenciais JSON

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo LICENSE para detalhes.

## Contato

Para suporte ou sugestões, entre em contato através de issues no GitHub. 