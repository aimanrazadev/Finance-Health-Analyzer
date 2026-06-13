import '../styles/UIPrimitives.css';

const Skeleton = ({ rows = 3 }) => (
  <div className="skeleton-stack" aria-label="Loading content">
    {Array.from({ length: rows }).map((_, index) => (
      <span className="skeleton-line" key={index} />
    ))}
  </div>
);

export default Skeleton;
