import { useEffect, useState } from 'react';
import api from '../utils/api';
import AppSelect from './AppSelect';
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
      <span className="category-dropdown-label">{label}</span>
      <AppSelect
        value={value}
        onChange={onChange}
        ariaLabel={label}
        options={[
          { value: '', label: 'Select category' },
          ...categories.map((category) => ({ value: category.id, label: category.name })),
        ]}
      />
    </div>
  );
};

export default CategoryDropdown;
