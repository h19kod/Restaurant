import { useState } from 'react'

export default function TestPage() {
  const [count, setCount] = useState(0)

  const handleClick = () => {
    setCount(c => c + 1)
    alert('Button clicked! Count: ' + (count + 1))
  }

  const handleLogin = async () => {
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=admin&password=admin123'
      })
      const data = await res.json()
      alert('Response: ' + JSON.stringify(data))
    } catch (err) {
      alert('Error: ' + err.message)
    }
  }

  return (
    <div style={{ padding: 50, textAlign: 'center' }}>
      <h1>Test Page</h1>
      <p>Count: {count}</p>
      <button 
        onClick={handleClick}
        style={{ padding: 20, fontSize: 20, margin: 10 }}
      >
        Test Button
      </button>
      <br/><br/>
      <button 
        onClick={handleLogin}
        style={{ padding: 20, fontSize: 20, background: 'blue', color: 'white' }}
      >
        Login Direct
      </button>
    </div>
  )
}
