import { expect, test } from 'bun:test';
import { act } from 'react';
import { testRender } from '@opentui/react/test-utils';
import { App } from '../src/app';
import { ChatController } from '../src/chat';

test('wide layout renders the cast and starter keys fill and submit the composer', async () => {
  const requests: any[] = [];
  const chat = new ChatController(request => requests.push(request));
  chat.receive({ type: 'ready', configured: true, demo: true, search: false });
  const view = await testRender(<App chat={chat} onQuit={() => {}} />, { width: 120, height: 40 });
  try {
    await view.renderOnce();
    const initial = view.captureCharFrame();
    expect(initial).toContain('THE DEN');
    expect(initial).toContain('THE CAST');
    expect(initial).toContain('DEMO');
    expect(initial).toContain('YOUR TURN');
    await act(async () => { view.mockInput.pressKey('F3'); });
    await view.renderOnce();
    expect(view.captureCharFrame()).toContain('Who is Kruti?');
    await act(async () => { view.mockInput.pressEnter(); });
    expect(requests[0]).toMatchObject({ type: 'chat', text: 'Tell me about Bhediya. Who is Kruti?' });
    await act(async () => {
      chat.receive({ type: 'tool', id: '1', name: 'get_bhediya_dossier' });
      chat.receive({ type: 'delta', id: '1', text: 'Meet Kruti, the wolf.' });
    });
    await view.renderOnce();
    expect(view.captureCharFrame()).toContain('Meet Kruti, the wolf.');
    expect(view.captureCharFrame()).toContain("Bhediya's field notes");
    await act(async () => { await view.mockInput.typeText('next question'); view.mockInput.pressEnter(); });
    await view.renderOnce();
    expect(requests.length).toBe(1);
    expect(view.captureCharFrame()).toContain('next question');
    // A lone ESC waits briefly for a possible terminal escape sequence.
    await act(async () => { view.mockInput.pressEscape(); await Bun.sleep(100); });
    expect(requests.at(-1)).toEqual({ type: 'cancel' });
    await act(async () => { chat.receive({ type: 'cancelled', id: '1' }); view.mockInput.pressKey('n', { ctrl: true }); });
    expect(requests.at(-1)).toEqual({ type: 'reset' });
  } finally { await act(async () => view.renderer.destroy()); }
});

test('compact layout keeps composer, help and missing-key guidance visible', async () => {
  const chat = new ChatController(() => {});
  chat.receive({ type: 'ready', configured: false, demo: false, search: false });
  const view = await testRender(<App chat={chat} onQuit={() => {}} />, { width: 60, height: 24 });
  try {
    await view.renderOnce();
    const frame = view.captureCharFrame();
    expect(frame).not.toContain('THE CAST');
    expect(frame).toContain('GOOGLE_API_KEY');
    expect(frame).toContain('YOUR TURN');
    expect(frame).toContain('ctrl+c quit');
    await act(async () => { view.mockInput.pressKey('F1'); });
    await view.renderOnce();
    expect(view.captureCharFrame()).toContain('A FEW SHORTCUTS');
  } finally { await act(async () => view.renderer.destroy()); }
});

test('multiline paste is one message and history remains scrollable after long replies', async () => {
  const requests: any[] = [];
  const chat = new ChatController(request => requests.push(request));
  chat.receive({ type: 'ready', configured: true, demo: false, search: false });
  const view = await testRender(<App chat={chat} onQuit={() => {}} />, { width: 80, height: 30 });
  try {
    await act(async () => { await view.mockInput.pasteBracketedText('Bhalu\nand Bhediya'); view.mockInput.pressEnter(); });
    expect(requests[0].text).toBe('Bhalu\nand Bhediya');
    await act(async () => {
      chat.receive({ type: 'text', id: '1', text: Array.from({ length: 45 }, (_, i) => `A bit of lore ${i}`).join('\n') });
      chat.receive({ type: 'done', id: '1' });
    });
    await view.renderOnce();
    expect(view.captureCharFrame()).toContain('A bit of lore 44');
    await act(async () => { view.mockInput.pressKey('\x1b[5~'); });
    await view.renderOnce();
    expect(view.captureCharFrame()).not.toContain('A bit of lore 44');
  } finally { await act(async () => view.renderer.destroy()); }
});
