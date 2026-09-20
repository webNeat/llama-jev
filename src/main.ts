import { server } from './server.js'

const req = {
  model: '',
  state:
    "Our API integration started returning 500 errors on every request about 20 minutes ago, and we can't process any customer orders until this is fixed.",
  questions: {
    department: {
      type: 'choice',
      instructions: 'Which team should handle this',
      criteria: {
        billing: 'Payment or subscription issues',
        technical: 'Bugs or integration problems',
        sales: 'Pricing or account questions',
      },
    },
    is_urgent: {
      type: 'choice',
      instructions: 'The message conveys urgency or time-sensitivity',
      criteria: { yes: null, no: null },
    },
  },
}

server.listen(3000, async () => {
  const start = performance.now()
  const res = await fetch('http://localhost:3000', {
    method: 'POST',
    body: JSON.stringify(req),
  })
  const data = await res.json()
  const duration = Math.floor(performance.now() - start)

  console.log(duration)
  console.log(JSON.stringify(data, null, 2))
  server.close()
})
