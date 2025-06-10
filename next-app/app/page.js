import PostViewer from './PostViewer'

// 這個頁面現在是一個簡單的伺服器元件，
// 它會渲染 PostViewer 客戶端元件。
export default function Home() {
  return (
    <main>
      <PostViewer />
    </main>
  )
} 