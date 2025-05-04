# TripIntelAI Command Line Interface

This README explains how to use the command-line interface and testing tools for TripIntelAI, which allows you to plan trips by entering natural language queries.

## Prerequisites

1. Make sure you have all the required dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up your environment variables in a `.env` file:
   ```
   ANTHROPIC_API_KEY=your_anthropic_key
   GOOGLE_PLACES_API_KEY=your_google_places_key
   ```

## CLI Applications

You have two options to run the TripIntelAI command line interface:

### Option 1: Using the Mock Graph Implementation

This is faster as it uses the mock graph implementation:

```bash
python main.py
```

### Option 2: Using Individual Components

This runs through each individual component in the pipeline:

```bash
python main_components.py
```

## API Testing Tools

### Command Line API Tester

To test the API endpoint from the command line:

```bash
python test_api.py --query "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people"
```

Options:
- `--query`, `-q`: The travel query to process (default is a sample query)
- `--url`, `-u`: The API endpoint URL (default is http://localhost:8000/chat)
- `--mock`, `-m`: Use the mock API endpoint on port 8001
- `--verbose`, `-v`: Print verbose output

### Streamlit Web Interface

For a graphical interface to test the API, run:

```bash
streamlit run app_api_ui.py
```

This will open a web interface where you can:
- Select between the normal API or mock API
- Enter your travel query or load an example query
- See a visual representation of the processing stages
- View the generated itinerary in a nicely formatted way

## How to Use the CLI

1. When you run either of the CLI applications, you'll be greeted with a welcome message.

2. Enter your travel query when prompted. For example:
   - "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people"
   - "Plan a family vacation to Paris in summer for 5 days with focus on museums"

3. You'll see a loading spinner with status messages while your request is being processed.

4. Once processing is complete, you'll see your personalized travel itinerary.

5. You can then choose to plan another trip or exit the application.

## Example Query

```
I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people with focus on museums and good restaurants
```

## Features

- Loading spinner with status updates
- Informative travel facts displayed during processing
- Step-by-step travel planning pipeline
- Error handling for invalid queries
- Easy-to-read itinerary output
- API testing capabilities

## Troubleshooting

If you encounter any issues:

1. Make sure your environment variables are correctly set in the `.env` file
2. Check that all dependencies are installed
3. Ensure your query has all the necessary information (source, destination, dates, number of people)
4. For API testing, verify that the server is running on the expected port

## Notes

This is a command-line interface and testing suite for the TripIntelAI travel planning system. For the web-based version, refer to the main project documentation. 