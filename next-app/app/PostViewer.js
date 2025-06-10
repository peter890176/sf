'use client';

import 'bootstrap/dist/css/bootstrap.min.css';
import { useState, useEffect } from 'react';

// 自訂 CSS
const customCss = `
  .category-title {
    text-transform: capitalize;
    border-bottom: 2px solid #dee2e6;
    padding-bottom: 0.5rem;
    margin-top: 2rem;
  }
  .card {
    transition: transform .2s;
  }
  .card:hover {
    transform: scale(1.02);
  }
  .card-text {
    white-space: pre-wrap;
    word-break: break-word;
  }
  .card-img-top {
    max-height: 400px;
    object-fit: cover;
  }
`;

export default function PostViewer() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // 從環境變數讀取 API 的絕對路徑
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || '/api/posts';

    // 在客戶端掛載後，從 API 路由獲取資料
    fetch(apiUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(fetchedData => {
        setData(fetchedData);
        setLoading(false);
      })
      .catch(error => {
        setError(error);
        setLoading(false);
      });
  }, []); // 空依賴陣列確保只執行一次

  // 在客戶端動態載入 Bootstrap JS
  useEffect(() => {
    require('bootstrap/dist/js/bootstrap.bundle.min.js');
  }, []);

  if (loading) {
    return <div className="container mt-5"><h1>載入中...</h1></div>;
  }

  if (error) {
    return <div className="container mt-5"><h1>發生錯誤: {error.message}</h1></div>;
  }

  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="container mt-5">
        <div className="alert alert-warning" role="alert">
          目前 Redis 中沒有找到任何資料，請先執行爬蟲。
        </div>
      </div>
    );
  }

  return (
    <>
      <style>{customCss}</style>
      <div className="container mt-4">
        <h1 className="mb-4 text-center">Facebook 粉絲團貼文資料</h1>

        {Object.entries(data).map(([category, posts]) => (
          <div key={category}>
            <h2 className="category-title">{category}</h2>
            <div className="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4 mt-2">
              {posts.map(post => (
                <div className="col" key={post.UID}>
                  <div className="card h-100 shadow-sm">
                    {post.ImageURL && <img src={post.ImageURL} className="card-img-top" alt="貼文圖片" />}
                    <div className="card-body">
                      <h5 className="card-title">
                        <a href={post.PostURL} target="_blank" rel="noopener noreferrer">前往貼文</a>
                      </h5>
                      <p className="card-text">{post.Content}</p>
                    </div>
                    <div className="card-footer text-muted">
                      <ul className="list-group list-group-flush">
                        <li className="list-group-item">👍 心情: {post.ReactionCount}</li>
                        <li className="list-group-item">💬 留言: {post.ResponseCount}</li>
                        <li className="list-group-item">🔁 分享: {post.ShareCount}</li>
                      </ul>
                    </div>
                    {post.VideoURL && (
                      <div className="card-footer">
                        <a href={post.VideoURL} target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm">觀看影片</a>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
} 