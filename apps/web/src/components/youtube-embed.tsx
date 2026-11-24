"use client";

const YOUTUBE_PATTERN =
  /(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|live\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/;

export function youtubeVideoId(url: string | null | undefined): string | null {
  if (!url) return null;
  const match = YOUTUBE_PATTERN.exec(url);
  return match ? match[1] : null;
}

export function YouTubeEmbed({
  url,
  title,
}: {
  url: string;
  title: string;
}) {
  const videoId = youtubeVideoId(url);
  if (!videoId) return null;

  return (
    <div className="mt-3 space-y-2">
      <div className="aspect-video w-full overflow-hidden rounded-xl border border-line bg-black/60">
        <iframe
          className="h-full w-full"
          src={`https://www.youtube-nocookie.com/embed/${videoId}`}
          title={title}
          loading="lazy"
          allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
      <a
        href={`https://www.youtube.com/watch?v=${videoId}`}
        target="_blank"
        rel="noreferrer"
        className="text-xs text-accent hover:underline"
      >
        Assistir no YouTube
      </a>
    </div>
  );
}
