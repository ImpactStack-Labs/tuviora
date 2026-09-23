export async function getApiHealth(signal) {
  const response = await fetch('/api/health/', { signal })

  if (!response.ok) {
    throw new Error(`API returned HTTP ${response.status}`)
  }

  const data = await response.json()

  if (data.status !== 'ok') {
    throw new Error('Unexpected API health response')
  }

  return data
}
