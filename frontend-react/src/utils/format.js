export const formatCurrency = (value) => {
  if (value === null || value === undefined) return '0đ';
  // Use vi-VN to format with dot as thousands separator
  return new Intl.NumberFormat('vi-VN').format(Math.round(value)) + 'đ';
};
