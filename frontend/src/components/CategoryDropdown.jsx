import { useEffect, useState } from 'react';
import api from '../utils/api';
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

  return (
    <div className="category-dropdown">
      <label htmlFor="category-dropdown">{label}</label>
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
  );
};

export default CategoryDropdown;
