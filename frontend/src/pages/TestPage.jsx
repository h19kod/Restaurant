import { useState } from 'react'

export default function TestPage() {
  const [count, setCount] = useState(0)

  const handleClick = () => {
    setCount(c => c + 1)
    alert('Button clicked! Count: ' + (count + 1))
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
    </div>
  )
}
