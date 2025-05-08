document.addEventListener('DOMContentLoaded', function () {
  // Attach JWT token to protected requests
  const token = document.cookie
    .split('; ')
    .find((row) => row.startsWith('access_token='))
    ?.split('=')[1]
  if (token) {
    fetch('/dashboard', {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then((response) => {
      if (response.status === 401) {
        document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT'
        window.location.href = '/signin'
      }
    })
  }
})
