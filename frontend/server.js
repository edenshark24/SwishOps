const path = require('path');
const express = require('express');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3000;
const API_BASE_URL = process.env.API_BASE_URL || 'http://swishops-backend-svc';
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://swishops-ai-service-svc';

// Backend queries are fast DB reads; AI calls wait on the model, so allow longer.
const BACKEND_TIMEOUT_MS = 5000;
const AI_TIMEOUT_MS = 60000;

const AI_ENDPOINTS = {
    'recommend': '/api/ai/recommend',
    'weekly-picks': '/api/ai/weekly-picks',
};

app.use(express.json());

// Unreachable upstreams (and upstream 5xx) become a 503; upstream 4xx errors
// such as "Player not found" are passed through so the dashboard can show them.
function sendProxyError(res, err, target) {
    const upstream = err.response;
    if (upstream && upstream.status < 500) {
        return res.status(upstream.status).json(upstream.data);
    }
    console.error(`Proxy to ${target} failed: ${upstream ? `HTTP ${upstream.status}` : err.message}`);
    return res.status(503).json({ error: 'Service unavailable' });
}

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'views', 'dashboard.html'));
});

app.get('/health', (req, res) => {
    res.status(200).json({ status: 'healthy' });
});

app.get('/api/trends', async (req, res) => {
    try {
        const [up, down] = await Promise.all([
            axios.get(`${API_BASE_URL}/api/trends/up`, { timeout: BACKEND_TIMEOUT_MS }),
            axios.get(`${API_BASE_URL}/api/trends/down`, { timeout: BACKEND_TIMEOUT_MS }),
        ]);
        res.json({ up: up.data, down: down.data });
    } catch (err) {
        sendProxyError(res, err, 'backend');
    }
});

app.get('/api/games', async (req, res) => {
    try {
        const response = await axios.get(`${API_BASE_URL}/api/games/today`, { timeout: BACKEND_TIMEOUT_MS });
        res.json(response.data);
    } catch (err) {
        sendProxyError(res, err, 'backend');
    }
});

app.post('/api/ai', async (req, res) => {
    const { type, ...payload } = req.body || {};
    const endpoint = AI_ENDPOINTS[type];
    if (!endpoint) {
        return res.status(400).json({ error: 'type must be "recommend" or "weekly-picks"' });
    }

    try {
        const response = await axios.post(`${AI_SERVICE_URL}${endpoint}`, payload, { timeout: AI_TIMEOUT_MS });
        res.json(response.data);
    } catch (err) {
        sendProxyError(res, err, 'AI service');
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Frontend running on port ${PORT}`);
});
