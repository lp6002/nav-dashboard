// Vercel Edge Function - CORS-friendly proxy for Sina Finance
// 在服务端把 GBK 转成 UTF-8 返回，浏览器不需要做编码处理

export const config = {
  runtime: 'edge',
};

export default async function handler(request) {
  const url = new URL(request.url);
  const symbols = url.searchParams.get('symbols') || 'sh000001';

  const sinaUrl = `https://hq.sinajs.cn/list=${symbols}`;

  try {
    const resp = await fetch(sinaUrl, {
      headers: { 'Referer': 'https://finance.sina.com.cn/' },
    });
    // Sina 返回 GBK 编码 - Edge Runtime 的 Response 自动用 UTF-8，
    // 但 fetch 的原始字节流需要我们手动转换
    const buf = await resp.arrayBuffer();
    // GBK → UTF-8：用 TextDecoder
    const text = new TextDecoder('gbk').decode(buf);

    return new Response(text, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=10',
      },
    });
  } catch (e) {
    return new Response(`Error: ${e.message}`, {
      status: 500,
      headers: { 'Access-Control-Allow-Origin': '*' },
    });
  }
}
