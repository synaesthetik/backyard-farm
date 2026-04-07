import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import { handler } from './build/handler.js';

const PORT = process.env.PORT || 3000;

const server = createServer(handler);
const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', (req, socket, head) => {
  if (req.url === '/ws/dashboard') {
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit('connection', ws, req);
    });
  } else {
    socket.destroy();
  }
});

wss.on('connection', (ws) => {
  console.log('Dashboard WebSocket client connected');
  ws.send(JSON.stringify({ type: 'snapshot', zones: {}, nodes: {} }));
  ws.on('close', () => console.log('Dashboard WebSocket client disconnected'));
});

server.listen(PORT, () => {
  console.log(`Dashboard server listening on port ${PORT}`);
});
