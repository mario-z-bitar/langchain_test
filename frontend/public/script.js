// frontend/public/script.js
document.addEventListener('DOMContentLoaded', () => {
    // Get references to the HTML elements
    const queryInput = document.getElementById('query-input');
    const sendButton = document.getElementById('send-button');
    const resultsContainer = document.getElementById('results-container');

    // Add an event listener to the "Send Query" button
    sendButton.addEventListener('click', async () => {
        const query = queryInput.value.trim(); // Get the text from the input box, remove leading/trailing spaces

        // Basic validation: Don't send empty queries
        if (!query) {
            resultsContainer.innerHTML = '<p style="color: red;">Please enter a query.</p>';
            return; // Stop the function here
        }

        resultsContainer.innerHTML = '<p>Loading...</p>'; // Show a loading message while waiting

        try {
            // Make a POST request to your FastAPI backend's /query endpoint
            const response = await fetch('http://127.0.0.1:8000/query', {
                method: 'POST', // Specifies this is a POST request
                headers: {
                    'Content-Type': 'application/json' // Tells the server we're sending JSON
                },
                // Convert our JavaScript object { query: query } into a JSON string
                body: JSON.stringify({ query: query }) 
            });

            // Check if the response was successful (status code 200-299)
            if (!response.ok) {
                // If not successful, throw an error to be caught by the catch block
                throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
            }

            // Parse the JSON response from the FastAPI backend
            const data = await response.json();

            // Display the final LLM response on the page
            if (data && data.final_llm_response) {
                resultsContainer.innerHTML = `<p><strong>Agent Response:</strong> ${data.final_llm_response}</p>`;
            } else {
                resultsContainer.innerHTML = `<p style="color: orange;">No final LLM response found. Raw data: ${JSON.stringify(data)}</p>`;
            }

            queryInput.value = ''; // Clear the input field after sending
        } catch (error) {
            // Catch and display any errors during the fetch operation
            console.error('Error fetching data:', error);
            resultsContainer.innerHTML = `<p style="color: red;">Error: ${error.message}. Please ensure the FastAPI backend is running and accessible.</p>`;
        }
    });

    // Optional: Allow submitting on Enter key press in the input field
    queryInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendButton.click(); // Simulate a click on the button
        }
    });
});