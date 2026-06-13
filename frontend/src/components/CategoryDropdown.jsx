import { useEffect, useState } from 'react';
import api from '../utils/api';
import { getCategoryColor } from '../utils/categoryDisplay';
import '../styles/CategoryDropdown.css';

const CategoryDropdown = ({ value, onChange, label = 'Category' }) => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await api.get('/categories');
        setCategories(response.data);
      } catch {
        setError('Unable to load categories.');
      } finally {
        setLoading(false);
      }
    };

    fetchCategories();
  }, []);

  if (loading) {
    return <p className="category-loading">Loading categories...</p>;
  }

  if (error) {
    return <p className="category-error">{error}</p>;
  }

  const selectedCategory = categories.find((category) => String(category.id) === String(value));

  return (
    <div className="category-dropdown">
      <label htmlFor="category-dropdown">{label}</label>
      <div
        className="category-select-shell"
        style={{ '--category-color': getCategoryColor(selectedCategory) }}
      >
        <span className="category-select-dot" aria-hidden="true" />
        <select
          id="category-dropdown"
          value={value}
          onChange={onChange}
          className="category-select"
        >
          <option value="">Select category</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default CategoryDropdown;
