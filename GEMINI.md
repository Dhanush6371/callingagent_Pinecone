# AI Inbound Agent System

## Project Overview

This is an AI-powered inbound voice agent system built using LiveKit, designed specifically for restaurants to handle inbound calls, take orders, and provide customer service. The system uses modern AI technologies including Google's Gemini for language processing, Deepgram for speech recognition and synthesis, and other plugins to provide a seamless voice-based interaction experience.

The system is implemented in Python and is structured around:

- **Inbound SIP Trunk Management**: Sets up SIP trunks to receive inbound calls.
- **Dispatch Rule Configuration**: Routes inbound calls to the appropriate AI agent.
- **AI Voice Agent**: Processes voice input, handles conversations, and manages orders.
- **Multi-language Support**: Supports English, Telugu, and Hindi for diverse customer bases.

## Project Architecture

The system consists of multiple components:

1.  **`inbound_trunk.py`**: Creates and manages SIP inbound trunk configuration in LiveKit.
2.  **`dispatch_rule.py`**: Configures how inbound calls are dispatched to agents.
3.  **`agent.py`**: The main voice agent implementation that handles real-time voice conversations.
4.  **`prompts.py`**: Contains AI instructions, the agent's persona, and restaurant menu information.
5.  **`db.py`**: Manages the connection to a MongoDB database for storing order information.
6.  **`.env`**: Holds environment variables for API keys and configuration.

The system uses LiveKit for real-time communication, Google's Gemini as the core language model, Deepgram for speech-to-text and text-to-speech, and Silero VAD for voice activity detection.

## Building and Running

### Prerequisites
- Python 3.9+
- pip
- MongoDB instance

### Setup Process

1.  **Create Virtual Environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables**
    Create a `.env` file with the following variables:
    ```bash
    LIVEKIT_API_KEY=your_livekit_api_key
    LIVEKIT_SECRET_KEY=your_livekit_secret
    TWIML_USERNAME=your_twiml_username
    TWIML_PASSWORD=your_twiml_password
    GOOGLE_API_KEY=your_google_api_key
    DEEPGRAM_API_KEY=your_deepgram_api_key
    MONGO_URI=your_mongodb_connection_string
    INBOUND_ALLOWED_NUMBERS=comma_separated_list_of_allowed_numbers  # Optional
    ```

4.  **Register SIP Inbound Trunk**
    Run this script once to create the SIP trunk in LiveKit:
    ```bash
    python inbound_trunk.py
    ```

5.  **Register SIP Dispatch Rule**
    Run this script after the trunk is created to configure call routing:
    ```bash
    python dispatch_rule.py
    ```

6.  **Start the Voice Agent**
    This command runs the AI voice assistant that handles calls:
    ```bash
    python agent.py console
    ```

## Key Features

1.  **Multi-language Support**: Automatically detects and responds in the customer's preferred language (English, Telugu, Hindi).
2.  **Order Management**: Takes food orders with customer details (name, phone, address) and saves them to a MongoDB database.
3.  **Menu Knowledge**: Has built-in knowledge of restaurant menu items, prices, and availability.
4.  **Real-time Conversation**: Handles natural conversation flow with voice interruptions and confirmations.
5.  **Database Integration**: Persists order data for fulfillment and record-keeping.

## Development Conventions

- The system follows an event-driven architecture using LiveKit's agent framework.
- All API keys and sensitive information are stored in environment variables and loaded via `dotenv`.
- The AI agent is designed to handle multiple languages within a single conversational session.
- Error handling is implemented for common failure scenarios like missing API keys and conflicting SIP configurations.
- The `prompts.py` file centralizes all instructional and contextual information for the LLM.
