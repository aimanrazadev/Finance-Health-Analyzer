import { useEffect, useMemo, useState } from 'react';
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
  const [friends, setFriends] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [selectedFriend, setSelectedFriend] = useState(null);
  const [search, setSearch] = useState('');
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const loadFriends = async () => {
    setLoading(true);
    setError('');
    try {
      const [friendsResponse, dashboardResponse] = await Promise.all([
        api.get('/friends', { headers }),
        api.get('/friends/dashboard', { headers }),
      ]);
      setFriends(friendsResponse.data);
      setDashboard(dashboardResponse.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load friends.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadFriends();
    }
  }, [token]);

  const addFriend = async (event) => {
    event.preventDefault();
    if (!name.trim()) return;
    setError('');
    setMessage('');
    try {
      await api.post('/friends', { name: name.trim() }, { headers });
      setName('');
      setMessage('Friend saved. Matching transactions were linked automatically.');
      await loadFriends();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Unable to save friend.');
    }
  };

  const hideFriend = async (friendId) => {
    setError('');
    setMessage('');
    try {
      await api.delete(`/friends/${friendId}`, { headers });
      setMessage('Friend hidden. Existing transaction history is kept safe.');
      setSelectedFriend(null);
      await loadFriends();
    } catch (err) {
      console.error(err);
      setError('Unable to hide friend.');
    }
  };

  const openFriend = async (friendId) => {
    setError('');
    try {
      const response = await api.get(`/friends/${friendId}`, { headers });
      setSelectedFriend(response.data);
    } catch (err) {
      console.error(err);
      setError('Unable to load friend details.');
    }
  };

  const filteredFriends = friends.filter((friend) => (
    friend.name.toLowerCase().includes(search.trim().toLowerCase())
  ));

  return (
    <div>
      <Navigation />
      <main className="friends-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Friend tracking</p>
            <h1>Friends</h1>
            <p>Save friend names so matching transactions are grouped and removed from category review.</p>
          </div>
        </div>

        {message && <div className="surface-message success">{message}</div>}
        {error && <div className="surface-message error">{error}</div>}

        <section className="friends-summary">
          <div>
            <span>Active friends</span>
            <strong>{dashboard?.active_friends ?? 0}</strong>
          </div>
          <div>
            <span>Linked transactions</span>
            <strong>{dashboard?.linked_transactions ?? 0}</strong>
          </div>
        </section>

        <section className="friends-layout">
          <div className="friends-panel">
            <form className="friend-form" onSubmit={addFriend}>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Friend name"
              />
              <button className="primary-button" type="submit">Add Friend</button>
            </form>
            <input
              className="friend-search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search friends"
            />

            {loading ? (
              <div className="empty-state">Loading friends...</div>
            ) : filteredFriends.length === 0 ? (
              <div className="empty-state">No friends saved yet.</div>
            ) : (
              <div className="friends-list">
                {filteredFriends.map((friend) => (
                  <div className="friend-row" key={friend.id}>
                    <button type="button" onClick={() => openFriend(friend.id)}>
                      <strong>{friend.name}</strong>
                      <span>{friend.normalized_name}</span>
                    </button>
                    <button className="table-button danger" onClick={() => hideFriend(friend.id)}>
                      Hide
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="friend-detail-panel">
            {!selectedFriend ? (
              <div className="empty-state">Select a friend to see linked transactions.</div>
            ) : (
              <>
                <div className="section-heading">
                  <div>
                    <h2>{selectedFriend.name}</h2>
                    <p>
                      {selectedFriend.summary.transaction_count} linked transaction
                      {selectedFriend.summary.transaction_count === 1 ? '' : 's'}
                    </p>
                  </div>
                  <strong>{moneyFormatter.format(selectedFriend.summary.net_amount)}</strong>
                </div>
                <div className="friend-transaction-list">
                  {selectedFriend.transactions.length === 0 ? (
                    <div className="empty-state">No linked transactions yet.</div>
                  ) : selectedFriend.transactions.map((transaction) => (
                    <div className="friend-transaction-row" key={transaction.id}>
                      <div>
                        <strong>{transaction.description}</strong>
                        <span>{new Date(transaction.date).toLocaleDateString()} - {transaction.transaction_type}</span>
                      </div>
                      <b>{moneyFormatter.format(transaction.amount)}</b>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </section>
      </main>
    </div>
  );
};

export default Friends;
