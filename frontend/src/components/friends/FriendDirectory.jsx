const FriendDirectory = ({
  friends,
  loading,
  name,
  search,
  selectedFriendId,
  onAddFriend,
  onOpenFriend,
  onNameChange,
  onSearchChange,
}) => (
  <section className="friends-panel">
    <div className="section-heading compact">
      <div>
        <h2>Friend Directory</h2>
        <p>Add a name or select a saved friend.</p>
      </div>
    </div>

    <form className="friend-form" onSubmit={onAddFriend}>
      <input
        value={name}
        onChange={(event) => onNameChange(event.target.value)}
        placeholder="Friend name"
      />
      <button className="primary-button" type="submit">Add Friend</button>
    </form>

    <input
      className="friend-search"
      value={search}
      onChange={(event) => onSearchChange(event.target.value)}
      placeholder="Search friends"
    />

    {loading ? (
      <div className="empty-state">Loading friends...</div>
    ) : friends.length === 0 ? (
      <div className="empty-state">No friends saved yet.</div>
    ) : (
      <div className="friends-list">
        {friends.map((friend) => (
          <article className={`friend-row ${selectedFriendId === friend.id ? 'active' : ''}`} key={friend.id}>
            <button className="friend-select-button" type="button" onClick={() => onOpenFriend(friend.id)}>
              <strong>{friend.name}</strong>
              <span>{friend.normalized_name}</span>
            </button>
          </article>
        ))}
      </div>
    )}
  </section>
);

export default FriendDirectory;
