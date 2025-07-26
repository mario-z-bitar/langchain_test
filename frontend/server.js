// frontend/server.js
const express = require('express');
const path = require('path'); // Node.js built-in module for working with file paths
const app = express();
const port = 3001; // The port your frontend server will run on

// Serve static files from the 'public' directory
// This tells Express to look for files like index.html, script.js, etc.,
// inside a folder named 'public' that will be next to this server.js file.
app.use(express.static(path.join(__dirname, 'public')));

// Define a route for the root URL ('/')
// When someone visits http://localhost:3001/, this function will run.
app.get('/', (req, res) => {
    // It sends the index.html file located in the 'public' directory.
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start the server and listen on the specified port
app.listen(port, () => {
    console.log(`Frontend server listening at http://localhost:${port}`);
});