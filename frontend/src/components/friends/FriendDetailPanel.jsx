const FriendDetailPanel = ({ friend, moneyFormatter }) => (
  <section className="friend-detail-panel">
    {!friend ? (
      <div className="empty-state friend-empty-state">Select a friend to see linked transactions.</div>
    ) : (
      <>
        <div className="section-heading compact">
          <div>
            <h2>{friend.name}</h2>
            <p>
              {friend.summary.transaction_count} linked transaction
              {friend.summary.transaction_count === 1 ? '' : 's'}
            </p>
          </div>
          <strong>{moneyFormatter.format(friend.summary.net_amount)}</strong>
        </div>
        <div className="friend-transaction-list">
          {friend.transactions.length === 0 ? (
            <div className="empty-state">No linked transactions yet.</div>
          ) : friend.transactions.map((transaction) => (
            <article className="friend-transaction-row" key={transaction.id}>
              <div>
                <strong>{transaction.extracted_merchant || transaction.merchant || transaction.description}</strong>
                <span>{transaction.description}</span>
                <small>{new Date(transaction.date).toLocaleDateString()} - {transaction.transaction_type}</small>
              </div>
              <b>{moneyFormatter.format(transaction.amount)}</b>
            </article>
          ))}
        </div>
      </>
    )}
  </section>
);

export default FriendDetailPanel;
