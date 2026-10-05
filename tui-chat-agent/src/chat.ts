import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';

export type Message = {
  id: string;
  role: 'you' | 'bhalu';
  text: string;
  tools: string[];
  state: 'pending' | 'done' | 'error' | 'cancelled';
};
export type ChatState = {
  connection: 'connecting' | 'ready' | 'closed';
  configured: boolean;
  demo: boolean;
  search: boolean;
  busy: boolean;
  resetting: boolean;
  messages: Message[];
  error: string;
};
export type BridgeEvent =
  | { type: 'ready'; configured: boolean; demo: boolean; search: boolean }
  | { type: 'delta' | 'text'; id: string; text: string }
  | { type: 'tool'; id: string; name: string }
  | { type: 'done' | 'cancelled'; id: string }
  | { type: 'error'; id?: string; message: string }
  | { type: 'fatal'; message: string }
  | { type: 'reset' };

export function parseEvent(line: string): BridgeEvent {
  const event = JSON.parse(line);
  if (!event || typeof event !== 'object') throw new Error('Invalid bridge event');
  switch (event.type) {
    case 'ready':
      if (['configured', 'demo', 'search'].every(key => typeof event[key] === 'boolean')) return event;
      break;
    case 'reset': return event;
    case 'fatal':
    case 'error':
      if (typeof event.message === 'string' && (event.id == null || typeof event.id === 'string')) return event;
      break;
    case 'delta':
    case 'text':
      if (typeof event.id === 'string' && typeof event.text === 'string') return event;
      break;
    case 'tool':
      if (typeof event.id === 'string' && typeof event.name === 'string') return event;
      break;
    case 'done':
    case 'cancelled':
      if (typeof event.id === 'string') return event;
  }
  throw new Error('Invalid bridge event');
}

// Render terminal control sequences as neither commands nor invisible text.
const plain = (text: string) => text.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, '').replace(/[\x00-\x08\x0b-\x1f\x7f]/g, '');

export class ChatController {
  private state: ChatState = {
    connection: 'connecting', configured: false, demo: false, search: false,
    busy: false, resetting: false, messages: [], error: '',
  };
  private listeners = new Set<() => void>();
  private active?: string;
  private sequence = 0;

  constructor(private write: (request: object) => void, private close: () => void = () => {}) {}
  getSnapshot = () => this.state;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  };
  private update(next: Partial<ChatState>) {
    this.state = { ...this.state, ...next };
    this.listeners.forEach(listener => listener());
  }
  private request(request: object): boolean {
    try { this.write(request); return true; }
    catch { this.receive({ type: 'fatal', message: 'The chat connection closed. Restart the app to reconnect.' }); return false; }
  }
  send(text: string): boolean {
    text = text.trim();
    if (!text || this.state.busy || this.state.resetting || !this.state.configured || this.state.connection !== 'ready') return false;
    if (text.length > 8000) {
      this.update({ error: 'That is a lot of lore. Keep each message under 8,000 characters.' });
      return false;
    }
    const id = String(++this.sequence);
    this.active = id;
    this.update({ busy: true, error: '', messages: [...this.state.messages,
      { id: `${id}-you`, role: 'you', text: plain(text), tools: [], state: 'done' },
      { id, role: 'bhalu', text: '', tools: [], state: 'pending' },
    ] });
    return this.request({ type: 'chat', id, text });
  }
  cancel() { if (this.active) this.request({ type: 'cancel' }); }
  reset() {
    if (this.state.connection !== 'ready' || this.state.resetting) return;
    this.active = undefined;
    this.update({ busy: false, resetting: true, error: '' });
    this.request({ type: 'reset' });
  }
  dispose() { this.close(); }
  receive(event: BridgeEvent) {
    if (event.type === 'ready') {
      this.update({ connection: 'ready', configured: event.configured, demo: event.demo, search: event.search });
      return;
    }
    if (event.type === 'reset') { this.update({ messages: [], resetting: false }); return; }
    if (event.type === 'fatal') {
      this.active = undefined;
      this.update({ connection: 'closed', busy: false, resetting: false, error: plain(event.message),
        messages: this.state.messages.map(message => message.state === 'pending' ? { ...message, state: 'error' } : message) });
      return;
    }
    if (event.type === 'error' && !event.id) { this.update({ error: plain(event.message) }); return; }
    if (event.id !== this.active) return;
    const complete = ['done', 'cancelled', 'error'].includes(event.type);
    const messages = this.state.messages.map(message => {
      if (message.id !== this.active) return message;
      switch (event.type) {
        case 'delta': return { ...message, text: message.text + plain(event.text) };
        case 'text': return { ...message, text: plain(event.text) };
        case 'tool': return { ...message, tools: [...new Set([...message.tools, event.name])] };
        case 'error': return { ...message, state: 'error' as const, text: message.text || plain(event.message) };
        case 'cancelled': return { ...message, state: 'cancelled' as const };
        case 'done': return { ...message, state: 'done' as const };
      }
    });
    if (complete) this.active = undefined;
    this.update({ messages, busy: !complete, error: event.type === 'error' ? plain(event.message) : '' });
  }
}

export function connectBridge(demo = false): ChatController {
  let child: ChildProcessWithoutNullStreams;
  let disposed = false;
  const controller = new ChatController(request => {
    if (!child || child.stdin.destroyed) throw new Error('Disconnected');
    child.stdin.write(JSON.stringify(request) + '\n');
  }, () => {
    disposed = true;
    child?.stdin.end();
    child?.kill();
  });
  const repo = fileURLToPath(new URL('../../', import.meta.url));
  const script = fileURLToPath(new URL('../bridge.py', import.meta.url));
  child = spawn('uv', ['run', '--frozen', '--no-sync', 'python', '-u', script, ...(demo ? ['--demo'] : [])], {
    cwd: repo, stdio: ['pipe', 'pipe', 'pipe'],
  });
  const lines = createInterface({ input: child.stdout });
  lines.on('line', line => {
    if (disposed) return;
    try { controller.receive(parseEvent(line)); }
    catch { controller.receive({ type: 'fatal', message: 'The agent returned an unreadable response. Restart the app.' }); child.kill(); }
  });
  // Drain SDK diagnostics without mixing them into the terminal or showing secrets.
  child.stderr.resume();
  child.stdin.on('error', () => {
    if (!disposed) controller.receive({ type: 'fatal', message: 'The chat connection closed. Restart the app.' });
  });
  child.on('error', () => controller.receive({ type: 'fatal', message: 'Could not start Python. Install uv, run uv sync in the repo root, then restart.' }));
  child.on('exit', () => {
    lines.close();
    if (!disposed && controller.getSnapshot().connection !== 'closed') controller.receive({ type: 'fatal', message: 'The agent stopped. Run uv sync in the repo root, then restart.' });
  });
  return controller;
}
