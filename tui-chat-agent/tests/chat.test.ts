import { expect, test } from 'bun:test';
import { ChatController, connectBridge, parseEvent } from '../src/chat';

function ready() {
  const requests: any[] = [];
  const chat = new ChatController(request => requests.push(request));
  chat.receive({ type: 'ready', configured: true, demo: true, search: false });
  return { chat, requests };
}

test('streaming preserves one turn, tools, and canonical final text', () => {
  const { chat, requests } = ready();
  expect(chat.send('  Meet Bhalu  ')).toBe(true);
  expect(chat.send('Second message')).toBe(false);
  expect(requests).toEqual([{ type: 'chat', id: '1', text: 'Meet Bhalu' }]);
  chat.receive({ type: 'tool', id: '1', name: 'get_aditya_profile' });
  chat.receive({ type: 'delta', id: '1', text: 'Hello ' });
  chat.receive({ type: 'delta', id: '1', text: 'there' });
  expect(chat.getSnapshot().messages[1]!.text).toBe('Hello there');
  chat.receive({ type: 'text', id: '1', text: 'Hello there!' });
  chat.receive({ type: 'done', id: '1' });
  expect(chat.getSnapshot().messages[1]).toMatchObject({ text: 'Hello there!', tools: ['get_aditya_profile'], state: 'done' });
  expect(chat.getSnapshot().busy).toBe(false);
});

test('cancellation and reset ignore late events without corrupting new conversations', () => {
  const { chat, requests } = ready();
  chat.send('hello');
  chat.cancel();
  expect(requests.at(-1)).toEqual({ type: 'cancel' });
  chat.receive({ type: 'cancelled', id: '1' });
  expect(chat.getSnapshot().messages[1]!.state).toBe('cancelled');
  chat.reset();
  expect(chat.send('too early')).toBe(false);
  chat.receive({ type: 'delta', id: '1', text: 'stale' });
  chat.receive({ type: 'reset' });
  expect(chat.getSnapshot().messages).toEqual([]);
  chat.send('new chat');
  chat.receive({ type: 'done', id: '1' });
  expect(chat.getSnapshot().busy).toBe(true);
  expect(requests.at(-1)).toEqual({ type: 'chat', id: '2', text: 'new chat' });
});

test('errors unlock retry and process failure stops pending replies', () => {
  const { chat } = ready();
  chat.send('hello');
  chat.receive({ type: 'error', id: '1', message: 'Quota exceeded' });
  expect(chat.getSnapshot().busy).toBe(false);
  expect(chat.getSnapshot().error).toBe('Quota exceeded');
  expect(chat.send('retry')).toBe(true);
  chat.receive({ type: 'fatal', message: 'Connection closed' });
  expect(chat.getSnapshot()).toMatchObject({ connection: 'closed', busy: false, error: 'Connection closed' });
  expect(chat.getSnapshot().messages.at(-1)!.state).toBe('error');
  expect(chat.send('retry')).toBe(false);
});

test('missing credentials, whitespace, oversized messages and malformed protocol are handled', () => {
  const chat = new ChatController(() => { throw new Error('should not write'); });
  chat.receive({ type: 'ready', configured: false, demo: false, search: false });
  expect(chat.send('hello')).toBe(false);
  const { chat: configured } = ready();
  expect(configured.send('  ')).toBe(false);
  expect(configured.send('x'.repeat(8001))).toBe(false);
  for (const value of ['null', '{', '{"type":"delta","id":"1"}', '{"type":"ready"}']) {
    expect(() => parseEvent(value)).toThrow();
  }
});

test('the real Python bridge handles a demo reply, cancellation and reset', async () => {
  const chat = connectBridge(true);
  async function waitFor(predicate: () => boolean) {
    const deadline = Date.now() + 8000;
    while (!predicate()) {
      if (Date.now() > deadline) throw new Error(JSON.stringify(chat.getSnapshot()));
      await Bun.sleep(20);
    }
  }
  try {
    await waitFor(() => chat.getSnapshot().connection !== 'connecting');
    expect(chat.getSnapshot().connection).toBe('ready');
    chat.send('Meet Bhediya');
    await waitFor(() => !chat.getSnapshot().busy);
    expect(chat.getSnapshot().messages.at(-1)!.text).toContain('Kruti Pandya');
    chat.send('roast');
    await waitFor(() => !!chat.getSnapshot().messages.at(-1)!.text);
    chat.cancel();
    await waitFor(() => !chat.getSnapshot().busy);
    expect(chat.getSnapshot().messages.at(-1)!.state).toBe('cancelled');
    chat.reset();
    await waitFor(() => !chat.getSnapshot().resetting);
    expect(chat.getSnapshot().messages).toEqual([]);
  } finally { chat.dispose(); }
}, 15000);
