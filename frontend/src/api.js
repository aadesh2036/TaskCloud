export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

const MAX_FILE_BYTES = 10 * 1024 * 1024;

export function createApi({ apiUrl, getToken, onUnauthorized }) {
  async function request(method, path, body) {
    const token = await getToken();
    if (!token) {
      onUnauthorized();
      throw new ApiError(401, 'Your session has ended. Log in again.');
    }
    let response;
    try {
      response = await fetch(apiUrl + path, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          ...(body !== undefined && { 'Content-Type': 'application/json' }),
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch {
      throw new ApiError(0, 'Could not reach the server. Check your connection and try again.');
    }
    if (response.status === 401) {
      onUnauthorized();
      throw new ApiError(401, 'Your session has ended. Log in again.');
    }
    if (response.status === 204) return null;
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new ApiError(response.status, payload?.message ?? `The server returned an error (${response.status}).`);
    }
    return payload;
  }

  return {
    listTasks: () => request('GET', '/tasks'),
    getProgress: () => request('GET', '/progress'),
    createTask: (fields) => request('POST', '/tasks', fields),
    updateTask: (id, fields) => request('PATCH', `/tasks/${id}`, fields),
    deleteTask: (id) => request('DELETE', `/tasks/${id}`),
    plan: (prompt) => request('POST', '/plan', { prompt }),
    getDownloadUrl: (id) => request('GET', `/tasks/${id}/attachment-url`),

    async uploadFile(id, file) {
      if (file.size > MAX_FILE_BYTES) throw new ApiError(413, 'Files can be at most 10 MB.');
      if (file.size === 0) throw new ApiError(400, 'That file is empty.');
      const { url, fields } = await request('POST', `/tasks/${id}/attachment-url`, {
        filename: file.name,
        size: file.size,
      });
      const form = new FormData();
      Object.entries(fields).forEach(([name, value]) => form.append(name, value));
      // S3 ignores any form field after the file, so the file must go last.
      form.append('file', file);
      let response;
      try {
        // No Authorization header: the signed fields are the permission.
        response = await fetch(url, { method: 'POST', body: form });
      } catch {
        throw new ApiError(0, 'The upload could not finish. Check your connection and try again.');
      }
      if (!response.ok) throw new ApiError(response.status, 'The upload was refused. The file may be over 10 MB.');
    },
  };
}
