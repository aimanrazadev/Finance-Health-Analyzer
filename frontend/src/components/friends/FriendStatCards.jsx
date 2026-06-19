const FriendStatCards = ({ dashboard }) => (
  <section className="friends-summary" aria-label="Friends summary">
    <article>
      <span>Active friends</span>
      <strong>{dashboard?.active_friends ?? 0}</strong>
    </article>
    <article>
      <span>Linked transactions</span>
      <strong>{dashboard?.linked_transactions ?? 0}</strong>
    </article>
  </section>
);

export default FriendStatCards;
