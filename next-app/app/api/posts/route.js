import { NextResponse } from 'next/server';
import { createClient } from 'redis';

export const dynamic = 'force-dynamic';

export async function GET(request) {
    // Redis Client Setup
    const redisHost = process.env.REDIS_HOST || 'localhost';
    const redisPort = process.env.REDIS_PORT || 6379;
    
    const redisClient = createClient({
        url: `redis://${redisHost}:${redisPort}`
    });

    redisClient.on('error', (err) => console.log('Redis Client Error', err));

    try {
        await redisClient.connect();

        const categoryKeys = await redisClient.keys('category:*');

        if (categoryKeys.length === 0) {
            return NextResponse.json({});
        }

        const allData = {};
        for (const key of categoryKeys) {
            const categoryName = key.split(':').pop();
            const postsRaw = await redisClient.hGetAll(key);
            
            const postsList = Object.values(postsRaw).map(post => JSON.parse(post));
            postsList.sort((a, b) => (b.ReactionCount || 0) - (a.ReactionCount || 0));

            allData[categoryName] = postsList;
        }
        
        await redisClient.quit();
        return NextResponse.json(allData);

    } catch (err) {
        console.error('Error fetching data from Redis:', err);
        await redisClient.quit();
        return NextResponse.json({ error: 'Failed to fetch data from Redis' }, { status: 500 });
    }
} 