import Skeleton from './Skeleton';
import { AnimateNumber } from './ui/AnimatedBlurNumber';

const currencyFormat = {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
};

const percentFormat = {
  maximumFractionDigits: 1,
};

const SummaryCard = ({
  label,
  value,
  helper,
  loading = false,
  tone = 'neutral',
  format = 'currency',
}) => {
  const valueNode = format === 'text'
    ? value
    : (
      <AnimateNumber
        value={Number(value || 0)}
        locale="en-IN"
        suffix={format === 'percent' ? '%' : ''}
        format={format === 'percent' ? percentFormat : currencyFormat}
      />
    );

  return (
    <article className={`metric-card metric-${tone} metric-format-${format}`}>
      <span>{label}</span>
      {loading ? <Skeleton rows={1} /> : <strong>{valueNode}</strong>}
      <small>{helper}</small>
    </article>
  );
};

export default SummaryCard;
