import { createCliRenderer } from '@opentui/core';
import { createRoot } from '@opentui/react';
import { App, colors } from './app';
import { connectBridge } from './chat';

const chat = connectBridge(process.argv.includes('--demo'));
try {
  const renderer = await createCliRenderer({
    exitOnCtrlC: false, backgroundColor: colors.bg, consoleMode: 'disabled',
    onDestroy: () => chat.dispose(),
  });
  createRoot(renderer).render(<App chat={chat} onQuit={() => renderer.destroy()} />);
} catch (error) {
  chat.dispose();
  console.error('Could not open The Den:', error instanceof Error ? error.message : error);
  process.exitCode = 1;
}
