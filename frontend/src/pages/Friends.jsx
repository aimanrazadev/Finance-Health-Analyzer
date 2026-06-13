import { useCallback, useEffect, useMemo, useState } from 'react';
import Navigation from '../components/Navigation';
import { useAuth } from '../hooks/useAuth';
import api, { getAuthHeaders } from '../utils/api';
import '../styles/Friends.css';

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
});

const Friends = () => {
  const { token } = useAuth();
  const headers = useMemo(() => getAuthHeaders(token), [token]);
  const [dashboard, setDashboard] = useState({ friends: [] });
  const [selectedFriendId, setSelectedFriendId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [friendName, setFriendName] = useState('');
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const loadFriends = useCallback(async () => {
    try {
      const response = await api.get('/friends', { headers, params: { search } });
      setDashboard(response.data);
      if (!selectedFriendId && response.data.friends.length > 0) {
        setSelectedFriendId(response.data.friends[0].id);
      }
    } catch (err) {
      console.error(err);
      setError('Unable to load friends.');
    }
  }, [headers, search, selectedFriendId]);

  const loadDetail = useCallback(async (friendId) => {
    if (!friendId) return;
    try {
      const response = await api.get(`/friends/${friendId}`, { headers });
      setDetail(response.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load friend details.');
    }
  }, [headers]);

  useEffect(() => {
    if (token) {
      queueMicrotask(() => {
        loadFriends();
      });
    }
  }, [loadFriends, token]);

  useEffect(() => {
    if (selectedFriendId) {
      queueMicrotask(() => {
        loadDetail(selectedFriendId);
      });
    }
  }, [loadDetail, selectedFriendId]);

  const addFriend = async (event) => {
    event.preventDefault();
    if (!friendName.trim()) return;
    try {
      await api.post('/friends', { name: friendName.trim() }, { headers });
      setFriendName('');
      setMessage('Friend added.');
      await loadFriends();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to add friend.');
    }
  };

  const deleteFriend = async (friendId, event) => {
    event.stopPropagation();
    if (!window.confirm('Delete this friend from the active list? Linked transactions will stay safe.')) return;
    await api.delete(`/friends/${friendId}`, { headers });
    if (selectedFriendId === friendId) {
      setSelectedFriendId(null);
      setDetail(null);
    }
    setMessage('Friend deleted from active list.');
    await loadFriends();
  };

  const selectedFriend = detail?.friend;

  return (
    <div>
      <Navigation />
      <main className="friends-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Friends</p>
            <h1>Friends</h1>
            <p>Group bank transactions by friend names and keep them out of the Categories correction queue.</p>
          </div>
        </div>

        {message && <div className="surface-message success">{message}</div>}
        {error && <div className="surface-message error">{error}</div>}

        <section className="friends-summary">
          <div><span>Total friends</span><strong>{dashboard.total_friends || 0}</strong></div>
          <div><span>Linked people</span><strong>{dashboard.friends?.length || 0}</strong></div>
          <div><span>Selected transactions</span><strong>{detail?.transactions?.length || 0}</strong></div>
        </section>

        <section className="friends-layout">
          <aside className="friends-panel">
            <form onSubmit={addFriend} className="friend-form">
              <input value={friendName} onChange={(event) => setFriendName(event.target.value)} placeholder="Add friend name" />
              <button className="primary-button" type="submit">Add</button>
            </form>
            <input className="friend-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search friends" />
            <div className="friend-list">
              {dashboard.friends?.map((friend) => (
                <button
                  type="button"
                  className={`friend-row ${selectedFriendId === friend.id ? 'active' : ''}`}
                  key={friend.id}
                  onClick={() => setSelectedFriendId(friend.id)}
                >
                  <button
                    type="button"
                    className="friend-delete-x"
                    onClick={(event) => deleteFriend(friend.id, event)}
                    aria-label={`Delete ${friend.name}`}
                  >
                    x
                  </button>
                  <span>{friend.name}</span>
                  <b>{friend.last_transaction_date ? new Date(friend.last_transaction_date).toLocaleDateString() : 'No transactions yet'}</b>
                  <small>View linked transactions</small>
                </button>
              ))}
            </div>
          </aside>

          <section className="friend-detail-panel">
            {!selectedFriend ? (
              <div className="empty-state">Select a friend to view linked transactions.</div>
            ) : (
              <>
                <div className="friend-detail-header">
                  <div>
                    <h2>{selectedFriend.name}</h2>
                    <p>{detail.transactions.length} linked bank transaction{detail.transactions.length === 1 ? '' : 's'}</p>
                  </div>
                </div>

                <div className="debt-table-wrapper">
                  <h3>Linked bank transactions</h3>
                  <table className="debt-table">
                    <thead>
                      <tr><th>Date</th><th>Description</th><th>Type</th><th>Amount</th><th>Merchant</th></tr>
                    </thead>
                    <tbody>
                      {detail.transactions.length === 0 ? (
                        <tr><td colSpan="5">No linked bank transactions yet.</td></tr>
                      ) : detail.transactions.map((transaction) => (
                        <tr key={transaction.id}>
                          <td>{new Date(transaction.date).toLocaleDateString()}</td>
                          <td>{transaction.description}</td>
                          <td>{transaction.transaction_type}</td>
                          <td>{moneyFormatter.format(transaction.amount)}</td>
                          <td>{transaction.merchant || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
        </section>
      </main>
    </div>
  );
};

export default Friends;
