/**
 * Read a JSON API response and surface any `{success: false, error}` payload
 * via console.error so it lands in the Quake console. Returns the parsed body
 * on success; throws on failure.
 *
 * 404 with a JSON body is treated as a "missing resource" non-error and
 * returned to the caller; HTTP errors without `{success: false}` still throw.
 */
export async function readApiResponse(response, label) {
  let data
  try {
    data = await response.json()
  } catch (parseError) {
    const message = `${label} returned non-JSON (status ${response.status})`
    console.error(message, parseError)
    throw new Error(message)
  }

  if (data && data.success === false && !data.conflict) {
    console.error(`${label} failed: ${data.error ?? '(no error message)'}`)
    const error = new Error(data.error || `${label} failed`)
    error.responseBody = data
    error.status = response.status
    throw error
  }

  return data
}
