import { getCategoryBadgeStyle, getCategoryName } from '../utils/categoryDisplay';
import '../styles/CategoryBadge.css';

const CategoryBadge = ({ category, name }) => {
  const label = getCategoryName(category, name || 'Uncategorized');

  return (
    <span className="category-badge" style={getCategoryBadgeStyle(category || label)}>
      <span className="category-badge-dot" aria-hidden="true" />
      {label}
    </span>
  );
};

export default CategoryBadge;
