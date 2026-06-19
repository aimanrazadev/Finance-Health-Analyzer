import { useEffect, useMemo, useState } from 'react';
import Navigation from '../components/Navigation';
import FriendDetailPanel from '../components/friends/FriendDetailPanel';
import FriendDirectory from '../components/friends/FriendDirectory';
import FriendStatCards from '../components/friends/FriendStatCards';
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

  const filteredFriends = friends.filter((friend) => {
    const term = search.trim().toLowerCase();
    if (!term) return true;
    return (
      friend.name.toLowerCase().includes(term)
      || friend.normalized_name.toLowerCase().includes(term)
    );
  });

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

        <FriendStatCards dashboard={dashboard} />

        <section className="friends-layout">
          <FriendDirectory
            friends={filteredFriends}
            loading={loading}
            name={name}
            search={search}
            selectedFriendId={selectedFriend?.id}
            onAddFriend={addFriend}
            onOpenFriend={openFriend}
            onNameChange={setName}
            onSearchChange={setSearch}
          />
          <FriendDetailPanel friend={selectedFriend} moneyFormatter={moneyFormatter} />
        </section>
      </main>
    </div>
  );
};

export default Friends;
