export const generateId = (): string => {
  return Math.random().toString(36).substring(2, 15) +
    Math.random().toString(36).substring(2, 15);
};

export const downloadJson = (data: any, filename: string): void => {
  const jsonString = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export const readJsonFile = (file: File): Promise<any> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target?.result as string);
        resolve(json);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = (error) => reject(error);
    reader.readAsText(file);
  });
};

export const exportAsPng = async (nodeId: string): Promise<void> => {
  const node = document.getElementById(nodeId);
  if (!node) return;

  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  if (!context) return;

  const scale = window.devicePixelRatio;
  canvas.width = node.offsetWidth * scale;
  canvas.height = node.offsetHeight * scale;
  context.scale(scale, scale);

  const data = await html2canvas(node);
  const link = document.createElement('a');
  link.download = 'mindmap.png';
  link.href = data.toDataURL('image/png');
  link.click();
};

export const calculateNodePosition = (
  parentPosition: { x: number; y: number },
  index: number,
  totalNodes: number,
  radius: number
): { x: number; y: number } => {
  const angle = (2 * Math.PI * index) / totalNodes;
  return {
    x: parentPosition.x + radius * Math.cos(angle),
    y: parentPosition.y + radius * Math.sin(angle),
  };
};

export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

export const getContrastColor = (hexcolor: string): string => {
  const r = parseInt(hexcolor.slice(1, 3), 16);
  const g = parseInt(hexcolor.slice(3, 5), 16);
  const b = parseInt(hexcolor.slice(5, 7), 16);
  const yiq = (r * 299 + g * 587 + b * 114) / 1000;
  return yiq >= 128 ? '#000000' : '#ffffff';
}; 