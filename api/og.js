import { ImageResponse } from '@vercel/og';

export const config = { runtime: 'edge' };

const SITE = '没有气的汽水';
const LOGO = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCI+PHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiByeD0iMTQiIGZpbGw9IiNEOTgyMkIiLz48cGF0aCBkPSJNMTUgMTggSDQ5IEw0NSA1NSBRNDQuNyA1OCA0MS43IDU4IEgyMi4zIFExOS4zIDU4IDE5IDU1IFoiIGZpbGw9IiNmZmYiLz48cGF0aCBkPSJNMTguNiAzMyBINDUuNCBMNDMuNCA1My42IFE0My4yIDU1LjYgNDEuMiA1NS42IEgyMi44IFEyMC44IDU1LjYgMjAuNiA1My42IFoiIGZpbGw9IiNGMkMyN0IiLz48bGluZSB4MT0iNDEiIHkxPSI1IiB4Mj0iMzYuNSIgeTI9IjMzIiBzdHJva2U9IiM2QjM0MTAiIHN0cm9rZS13aWR0aD0iNCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+PGNpcmNsZSBjeD0iMjkiIGN5PSI0NiIgcj0iMy4yIiBmaWxsPSJub25lIiBzdHJva2U9IiNmZmYiIHN0cm9rZS13aWR0aD0iMi4yIi8+PC9zdmc+';

// 只取标题里用到的字，Google Fonts 返回的子集很小
async function loadFont(text) {
  const css = await fetch(
    'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@700&text=' + encodeURIComponent(text)
  ).then((r) => r.text());
  const url = css.match(/src: url\((.+?)\) format/)?.[1];
  return url ? fetch(url).then((r) => r.arrayBuffer()) : null;
}

const h = (type, style, children) => ({ type, props: { style, children } });

export default async function handler(req) {
  const title = (new URL(req.url).searchParams.get('title') || SITE).slice(0, 80);
  const font = await loadFont(title + SITE + 'someget.cn').catch(() => null);

  const node = h('div', {
    width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
    padding: '72px 80px', background: '#FFF4E3', fontFamily: 'Noto Sans SC',
  }, [
    h('div', { display: 'flex', alignItems: 'center', gap: '20px' }, [
      { type: 'img', props: { src: LOGO, width: 72, height: 72 } },
      h('div', { fontSize: 36, color: '#B5651D' }, SITE),
    ]),
    h('div', { fontSize: title.length > 24 ? 60 : 72, lineHeight: 1.3, color: '#3D2310', display: 'flex' }, title),
    h('div', { fontSize: 30, color: '#B5651D' }, 'someget.cn'),
  ]);

  return new ImageResponse(node, {
    width: 1200,
    height: 630,
    fonts: font ? [{ name: 'Noto Sans SC', data: font, weight: 700, style: 'normal' }] : [],
    headers: { 'Cache-Control': 'public, max-age=86400, s-maxage=31536000, immutable' },
  });
}
