// Capture the actual OpenTUI cell buffer for the README, without API calls.
import { act } from 'react';
import { testRender } from '@opentui/react/test-utils';
import { App, colors } from '../src/app';
import { ChatController } from '../src/chat';
import { mkdir } from 'node:fs/promises';

const chat = new ChatController(() => {});
chat.receive({ type: 'ready', configured: true, demo: true, search: false });
const width = Number(process.argv[2] || 120);
const height = Number(process.argv[3] || 40);
const view = await testRender(<App chat={chat} onQuit={() => {}} />, { width, height });
const escape = (value: string) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
try {
  await view.renderOnce();
  const frame = view.captureSpans();
  const cellWidth = 9;
  const cellHeight = 19;
  const elements: string[] = [];
  for (const [row, line] of frame.lines.entries()) {
    let column = 0;
    for (const span of line.spans) {
      const fg = `rgb(${span.fg.toInts().slice(0, 3).join(',')})`;
      const bg = `rgb(${span.bg.toInts().slice(0, 3).join(',')})`;
      elements.push(`<rect x="${column * cellWidth}" y="${row * cellHeight}" width="${span.width * cellWidth}" height="${cellHeight}" fill="${bg}"/>`);
      if (span.text.trim()) elements.push(`<text x="${column * cellWidth}" y="${row * cellHeight + 14}" fill="${fg}" ${span.attributes & 1 ? 'font-weight="bold"' : ''} textLength="${span.width * cellWidth}" lengthAdjust="spacingAndGlyphs">${escape(span.text)}</text>`);
      column += span.width;
    }
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width * cellWidth}" height="${height * cellHeight}" viewBox="0 0 ${width * cellWidth} ${height * cellHeight}"><rect width="100%" height="100%" fill="${colors.bg}"/><g font-family="'SF Mono', Menlo, Consolas, monospace" font-size="14" xml:space="preserve">${elements.join('')}</g></svg>`;
  await mkdir(new URL('../docs/', import.meta.url), { recursive: true });
  await Bun.write(new URL(`../docs/preview-${width}.svg`, import.meta.url), svg);
  await Bun.write(`/tmp/bhalu-preview-${width}.txt`, view.captureCharFrame());
} finally { await act(async () => view.renderer.destroy()); }
