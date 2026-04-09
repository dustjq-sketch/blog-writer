import { useState, useEffect } from 'react'
import { MessageSquare, RefreshCw, ChevronDown, ChevronUp, User, Bot } from 'lucide-react'

const API = ''

function ConversationItem({ item }) {
  const [open, setOpen] = useState(false)
  const time = new Date(item.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
  const preview = item.user.length > 80 ? item.user.slice(0, 80) + '…' : item.user

  return (
    <div style={{
      background: '#111116', border: '1px solid #222228',
      borderRadius: 10, marginBottom: 8, overflow: 'hidden',
    }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', cursor: 'pointer' }}
      >
        <MessageSquare size={14} color="#4a5abf" style={{ flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, color: '#e0e0d8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {preview}
          </div>
          <div style={{ fontSize: 11, color: '#555', marginTop: 2 }}>{time}</div>
        </div>
        {open ? <ChevronUp size={13} color="#555" /> : <ChevronDown size={13} color="#555" />}
      </div>

      {open && (
        <div style={{ borderTop: '1px solid #1a1a20', padding: 16 }}>
          {/* 사용자 메시지 */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <User size={12} color="#c8a84e" />
              <span style={{ fontSize: 11, color: '#c8a84e', fontWeight: 600 }}>나</span>
            </div>
            <div style={{
              background: '#0f0f14', border: '1px solid #2a2a32',
              borderRadius: 8, padding: 12, fontSize: 13, color: '#e0e0d8',
              lineHeight: 1.7, whiteSpace: 'pre-wrap',
            }}>
              {item.user}
            </div>
          </div>

          {/* 어시스턴트 응답 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <Bot size={12} color="#3a7d5c" />
              <span style={{ fontSize: 11, color: '#3a7d5c', fontWeight: 600 }}>Claude</span>
            </div>
            <div style={{
              background: '#0a0d0a', border: '1px solid #1e2a1e',
              borderRadius: 8, padding: 12, fontSize: 13, color: '#e0e0d8',
              lineHeight: 1.7, whiteSpace: 'pre-wrap',
            }}>
              {item.assistant}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Conversations() {
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)

  const loadDates = async () => {
    const d = await fetch(`${API}/api/conversations/dates`).then(r => r.json()).catch(() => [])
    setDates(d)
    if (d.length > 0 && !selectedDate) {
      setSelectedDate(d[0])
    }
  }

  const loadItems = async (date) => {
    if (!date) return
    setLoading(true)
    const data = await fetch(`${API}/api/conversations/${date}`).then(r => r.ok ? r.json() : []).catch(() => [])
    setItems([...data].reverse())
    setLoading(false)
  }

  useEffect(() => { loadDates() }, [])
  useEffect(() => { loadItems(selectedDate) }, [selectedDate])

  const today = new Date().toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' })

  return (
    <div style={{ padding: '24px 28px', maxWidth: 820, margin: '0 auto' }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: '#e0e0d8', margin: 0 }}>
          대화 기록
        </h2>
        <p style={{ fontSize: 13, color: '#666', marginTop: 6 }}>
          텔레그램 Remote Claude Bot을 통해 주고받은 대화 내역입니다.
        </p>
      </div>

      {dates.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#444', padding: '60px 0', fontSize: 13 }}>
          <MessageSquare size={32} color="#333" style={{ margin: '0 auto 12px' }} />
          <div>아직 대화 기록이 없습니다.</div>
          <div style={{ fontSize: 12, color: '#333', marginTop: 6 }}>
            텔레그램 봇에 메시지를 보내면 여기에 기록됩니다.
          </div>
        </div>
      ) : (
        <>
          {/* 날짜 선택 */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
            {dates.map(d => (
              <button
                key={d}
                onClick={() => setSelectedDate(d)}
                style={{
                  background: selectedDate === d ? '#c8a84e' : '#111116',
                  color: selectedDate === d ? '#0a0a0d' : '#888',
                  border: `1px solid ${selectedDate === d ? '#c8a84e' : '#2a2a32'}`,
                  borderRadius: 6, padding: '5px 12px', fontSize: 12,
                  fontWeight: selectedDate === d ? 700 : 400,
                  cursor: 'pointer',
                }}
              >
                {d}
              </button>
            ))}
            <button
              onClick={() => { loadDates(); loadItems(selectedDate) }}
              style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}
            >
              <RefreshCw size={12} /> 새로고침
            </button>
          </div>

          {/* 대화 목록 */}
          {loading ? (
            <div style={{ textAlign: 'center', color: '#555', padding: '40px 0', fontSize: 13 }}>불러오는 중...</div>
          ) : items.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#444', padding: '40px 0', fontSize: 13 }}>
              이 날짜의 대화 기록이 없습니다.
            </div>
          ) : (
            <>
              <div style={{ fontSize: 12, color: '#555', marginBottom: 12 }}>
                총 {items.length}건
              </div>
              {items.map(item => (
                <ConversationItem key={item.id} item={item} />
              ))}
            </>
          )}
        </>
      )}
    </div>
  )
}
