import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { useKeyboard, useTerminalDimensions } from '@opentui/react';
import type { ScrollBoxRenderable, TextareaRenderable } from '@opentui/core';
import { ChatController, type Message } from './chat';

export const colors = {
  bg: '#171A18', panel: '#1F2420', elevated: '#262D27', line: '#39443A',
  ink: '#ECE6D5', muted: '#A1AD9F', dim: '#748272', amber: '#E4B079',
  sage: '#B3C9A0', rose: '#D99A8C',
};
const starters = [
  { label: 'Meet Bhalu', prompt: 'Who is Bhalu? Tell me about the bear.' },
  { label: 'Meet Bhediya', prompt: 'Tell me about Bhediya. Who is the wolf?' },
  { label: 'A gentle roast', prompt: 'Give me a gentle roast of Bhalu.' },
  { label: 'Their story', prompt: 'Tell me about both Bhalu and Bhediya.' },
];
const tools: Record<string, string> = {
  get_bhalu_profile: "Bhalu's field notes",
  get_bhalu_lore: 'The lore archive',
  get_bhediya_dossier: "Bhediya's field notes",
  search_web: 'Searching the web',
};

function Pulse({ label }: { label: string }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setTick(value => value + 1), 220);
    return () => clearInterval(timer);
  }, []);
  return <text fg={colors.amber}>{['◐', '◓', '◑', '◒'][tick % 4]} {label}</text>;
}

function Reply({ message }: { message: Message }) {
  const isBear = message.role === 'bhalu';
  return <box flexDirection="column" flexShrink={0} paddingLeft={2} paddingRight={2} paddingTop={1} paddingBottom={1}
    backgroundColor={isBear ? colors.panel : colors.bg} border={['left']} borderColor={isBear ? colors.amber : colors.sage}>
    <box flexDirection="row" gap={2} marginBottom={1}>
      <text fg={isBear ? colors.amber : colors.sage}><b>{isBear ? '●  BHALU' : '↗  YOU'}</b></text>
      <text fg={colors.dim}>{isBear ? 'resident bear' : 'pull up a chair'}</text>
    </box>
    {message.tools.length > 0 && <text fg={colors.dim} marginBottom={1}>
      {message.tools.map(name => `↳ ${tools[name] || 'Checking notes'}`).join('  ·  ')}
    </text>}
    {message.text && <text fg={message.state === 'error' ? colors.rose : colors.ink} wrapMode="word" selectable>{message.text}</text>}
    {message.state === 'pending' && <Pulse label={message.text ? 'Still a little more to say…' : 'The bear is gathering his thoughts…'} />}
    {message.state === 'cancelled' && <text fg={colors.dim}>Stopped. Take the conversation somewhere new.</text>}
    {message.state === 'error' && <text fg={colors.rose}>Could not finish this reply. You can try again.</text>}
  </box>;
}

function Cast({ demo, search }: { demo: boolean; search: boolean }) {
  return <box width={27} flexShrink={0} flexDirection="column" border={['left']} borderColor={colors.line} paddingLeft={3} paddingRight={1}>
    <text fg={colors.dim} marginBottom={1}>THE CAST</text>
    <text fg={colors.amber}>{'  ()___()\n  ( o.o )'}</text>
    <text fg={colors.amber} marginTop={1}><b>BHALU</b></text>
    <text fg={colors.ink}>The bear</text>
    <text fg={colors.muted} marginTop={1}>{'Builder. Professional\noverthinker. Your\nresident bear.'}</text>
    <text fg={colors.line} marginTop={1} marginBottom={1}>────────────────────</text>
    <text fg={colors.sage}>{'   /\\_/\\\n  ( o.o )'}</text>
    <text fg={colors.sage} marginTop={1}><b>BHEDIYA</b></text>
    <text fg={colors.ink}>The wolf</text>
    <text fg={colors.muted} marginTop={1}>{'Agent builder. The wolf.\nThe reason the bear\nhas this much lore.'}</text>
    <box flexGrow={1} />
    <text fg={colors.dim} marginBottom={1}>IN THE BACKPACK</text>
    <text fg={colors.sage}>✓ Curated field notes</text>
    <text fg={search ? colors.sage : colors.muted}>{search ? '✓ Live web search' : '○ Web search offline'}</text>
    <text fg={colors.dim} marginTop={1} marginBottom={1}>{demo ? 'Scripted preview.\nNo API calls.' : 'A little lore, a little love.\nFacts before fiction.'}</text>
  </box>;
}

export function App({ chat, onQuit }: { chat: ChatController; onQuit: () => void }) {
  const state = useSyncExternalStore(chat.subscribe, chat.getSnapshot);
  const { width, height } = useTerminalDimensions();
  const input = useRef<TextareaRenderable>(null);
  const scroll = useRef<ScrollBoxRenderable>(null);
  const [help, setHelp] = useState(false);
  const wide = width >= 105 && height >= 38;
  const compact = height < 30;
  const canSend = state.connection === 'ready' && state.configured && !state.busy && !state.resetting;

  const fill = (index: number) => { input.current?.setText(starters[index]!.prompt); input.current?.focus(); };
  const submit = () => {
    const text = input.current?.plainText.trim() || '';
    if (text === '/quit') { onQuit(); return; }
    if (text === '/help') { setHelp(value => !value); input.current?.clear(); return; }
    if (text === '/new') { chat.reset(); input.current?.clear(); return; }
    if (chat.send(text)) input.current?.clear();
  };
  useKeyboard(key => {
    if (key.ctrl && key.name === 'c') { key.preventDefault(); onQuit(); }
    else if (key.ctrl && key.name === 'n') { key.preventDefault(); chat.reset(); }
    else if (key.name === 'f1') { key.preventDefault(); setHelp(value => !value); }
    else if (key.name === 'escape') { key.preventDefault(); if (help) setHelp(false); else chat.cancel(); }
    else if (/^f[2-5]$/.test(key.name)) { key.preventDefault(); fill(Number(key.name.slice(1)) - 2); }
    else if (key.name === 'pageup' || key.name === 'pagedown') {
      key.preventDefault(); scroll.current?.scrollBy(key.name === 'pageup' ? -1 : 1, 'viewport');
    }
  });

  return <box width="100%" height="100%" backgroundColor={colors.bg} flexDirection="column" paddingLeft={width < 60 ? 1 : 3} paddingRight={width < 60 ? 1 : 3}>
    <box height={compact ? 3 : 4} flexShrink={0} flexDirection="row" alignItems="center" justifyContent="space-between" border={['bottom']} borderColor={colors.line}>
      <text fg={colors.ink}><span fg={colors.amber}>✳ </span><b> THE DEN</b><span fg={colors.dim}>{width >= 65 ? '   /   Bhalu & Bhediya' : ''}</span></text>
      <text fg={state.demo ? colors.amber : colors.sage}>{state.connection === 'closed' ? '○ OFFLINE' : state.connection === 'connecting' ? '○ CONNECTING' : state.demo ? '◌ DEMO' : state.configured ? '● LIVE' : '○ SETUP'}</text>
    </box>
    <box flexDirection="row" flexGrow={1} minHeight={0} marginTop={1} gap={3}>
      <box flexDirection="column" flexGrow={1} minWidth={0}>
        <scrollbox ref={scroll} flexGrow={1} minHeight={0} stickyScroll stickyStart={state.messages.length ? 'bottom' : 'top'}
          contentOptions={{ flexDirection: 'column', gap: 1, paddingRight: 1 }}
          scrollbarOptions={{ visible: state.messages.length > 0, trackOptions: { backgroundColor: colors.bg, foregroundColor: colors.line } }}>
          {state.messages.length === 0 && <box flexDirection="column" flexShrink={0} paddingLeft={2} paddingRight={2} paddingTop={compact ? 0 : 2}>
            {!compact && <box flexDirection="row" gap={5} marginBottom={1}>
              <text fg={colors.amber}>{'  ()___()\n  ( o.o )'}</text>
              <text fg={colors.rose}>{'\n  ♥'}</text>
              <text fg={colors.sage}>{'   /\\_/\\\n  ( o.o )'}</text>
            </box>}
            <text fg={colors.ink} marginTop={compact ? 0 : 1}><b>A bear. A wolf. A little bit of lore.</b></text>
            <text fg={colors.muted} marginTop={1} wrapMode="word">Pull up a chair. Ask about Bhalu, get to know Bhediya, or let the bear embarrass himself.</text>
            <text fg={colors.dim} marginTop={compact ? 1 : 2} marginBottom={1}>WHERE SHALL WE START?</text>
            <box flexDirection={width < 50 ? 'column' : 'row'} gap={1}>
              {starters.slice(0, 2).map((item, index) => <box key={item.label} flexGrow={1} flexBasis={width < 50 ? 'auto' : 0} border borderStyle="rounded" borderColor={colors.line} paddingLeft={1} paddingRight={1} onMouseDown={() => fill(index)}>
                <text fg={index === 0 ? colors.amber : colors.sage}>{`F${index + 2}  ${item.label}  ↗`}</text>
              </box>)}
            </box>
            {!compact && <box flexDirection="row" gap={1}>
              {starters.slice(2).map((item, index) => <box key={item.label} flexGrow={1} flexBasis={0} border borderStyle="rounded" borderColor={colors.line} paddingLeft={1} paddingRight={1} onMouseDown={() => fill(index + 2)}>
                <text fg={colors.muted}>{`F${index + 4}  ${item.label}  ↗`}</text>
              </box>)}
            </box>}
            {!compact && <text fg={colors.dim} marginTop={1}>{state.demo ? 'A scripted taste of the den. Try any of the prompts above.' : 'Real notes. Occasional bear puns. No invented lore.'}</text>}
          </box>}
          {state.messages.map(message => <Reply key={message.id} message={message} />)}
        </scrollbox>
        {help && <box flexDirection="column" flexShrink={0} backgroundColor={colors.elevated} padding={1} marginTop={1}>
          <text fg={colors.sage}><b>A FEW SHORTCUTS</b></text>
          <text fg={colors.ink}>{'Enter send · Shift+Enter / Ctrl+J newline\nEsc stop reply · PgUp/PgDn scroll · F2–F5 prompts\nCtrl+N new chat · Ctrl+C quit · F1 close help\n/new /help /quit also work. Chats last for this session.'}</text>
        </box>}
        {state.connection === 'ready' && !state.configured && <box flexShrink={0} padding={1} backgroundColor={colors.elevated}>
          <text fg={colors.amber} wrapMode="word">The bear needs a key. Add GOOGLE_API_KEY to the repo-root .env and restart. Just exploring? Run bun run demo.</text>
        </box>}
        {!!state.error && <text fg={colors.rose} flexShrink={0} marginTop={1} wrapMode="word">{state.error}</text>}
        <box flexDirection="column" flexShrink={0} border borderStyle="rounded" borderColor={canSend ? colors.amber : colors.line}
          backgroundColor={colors.panel} paddingLeft={1} paddingRight={1} marginTop={1} title={state.busy ? ' BHALU HAS THE FLOOR · ESC TO STOP ' : ' YOUR TURN '}>
          <textarea ref={input} id="composer" height={compact ? 2 : 3} focused textColor={colors.ink}
            backgroundColor={colors.panel} focusedBackgroundColor={colors.panel} cursorColor={colors.amber}
            placeholderColor={colors.dim} placeholder={state.busy ? 'You can draft your next thought while he talks…' : 'Ask the bear something…'}
            keyBindings={[{ name: 'return', action: 'submit' }, { name: 'return', shift: true, action: 'newline' }, { name: 'j', ctrl: true, action: 'newline' }]}
            onSubmit={submit} />
        </box>
        <box flexDirection="row" justifyContent="space-between" flexShrink={0} marginTop={0} marginBottom={1}>
          <text fg={colors.muted}>{state.busy ? 'esc stop' : state.resetting ? 'Starting fresh…' : 'enter send'}<span fg={colors.dim}>{width >= 65 ? '  ·  shift+enter newline' : ''}</span></text>
          <text fg={colors.dim}>f1 help</text>
        </box>
      </box>
      {wide && <Cast demo={state.demo} search={state.search} />}
    </box>
    <box height={2} flexShrink={0} border={['top']} borderColor={colors.line} flexDirection="row" justifyContent="space-between">
      <text fg={colors.dim}>{width >= 65 ? 'a little lore, a little love.' : 'Bhalu & Bhediya'}</text>
      <text fg={colors.muted}>{width >= 65 ? 'ctrl+n new chat  ·  ' : ''}ctrl+c quit</text>
    </box>
  </box>;
}
