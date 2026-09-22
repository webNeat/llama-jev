import { createServer, IncomingMessage, ServerResponse } from 'node:http'
import typia from 'typia'
import { jev } from './jev.js'
import type { Request } from './types.js'

const isRequest = typia.createIs<Request>()

export const server = createServer(async (req, res) => {
  try {
    if (req.method === 'POST' && req.url === '/v1/systemone') {
      const body = await json(req)
      if (!isRequest(body)) throw new Error(`Invalid request body`)
      return sendJson(res, await jev(body))
    }
    sendJson(res, { error: 'Not found' }, 404)
  } catch (error) {
    sendJson(res, { error: String(error) }, 400)
  }
})

async function json(req: IncomingMessage, limit = 1024 * 1024) {
  let size = 0
  const chunks = []
  for await (const chunk of req) {
    size += chunk.length
    if (size > limit) {
      throw new Error('Body too large')
    }
    chunks.push(chunk)
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'))
}

function sendJson(res: ServerResponse, data: unknown, status = 200) {
  res.writeHead(status, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify(data))
}
