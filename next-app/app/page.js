import PostViewer from './PostViewer';

// 這個頁面現在是一個簡單的伺服器元件，
// 它只負責渲染客戶端元件，而不再獲取資料。
export default function Home() {
  return (
    <main>
      <PostViewer />
    </main>
  );
} 