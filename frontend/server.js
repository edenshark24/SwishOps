const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;
const API_BASE_URL = process.env.API_BASE_URL || 'http://swishops-backend-svc';

app.use(express.json());

app.get('/', (req, res) => {
    res.status(200).send('SwishOps Frontend Service is up and running!');
});

app.get('/dashboard', async (req, res) => {
    res.json({ title: "SwishOps NBA Analytics Dashboard", backendTarget: API_BASE_URL });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Frontend running on port ${PORT}`);
});
