import { createServer } from 'http';
import { handler } from './build/handler.js';

const PORT = process.env.PORT || 3000;

const server = createServer(handler);

server.listen(PORT, () => {
  console.log(`Dashboard server listening on port ${PORT}`);
});
