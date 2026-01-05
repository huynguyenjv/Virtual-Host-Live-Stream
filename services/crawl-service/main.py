"""
main.py
Crawler Service Entry Point
"""

import sys
import argparse
from config import Config
from listener import TikTokLiveCrawler


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="TikTok Live Crawler Service"
    )
    
    parser.add_argument(
        "--username",
        type=str,
        help="TikTok username to crawl (overrides env)"
    )
    
    parser.add_argument(
        "--queue-type",
        type=str,
        choices=["redis", "rabbitmq", "memory"],
        help="Queue type (overrides env)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    return parser.parse_args()


def main():
    """Main function"""
    args = parse_args()
    
    try:
        # Load config
        config = Config()
        
        # Override với command line args
        if args.username:
            config.TIKTOK_USERNAME = args.username
        
        if args.queue_type:
            config.QUEUE_TYPE = args.queue_type
        
        if args.debug:
            config.DEBUG = True
        
        # Banner
        print("\n" + "=" * 60)
        print("  TIKTOK LIVE CRAWLER SERVICE")
        print("=" * 60)
        print(f"  Target    : @{config.TIKTOK_USERNAME}")
        print(f"  Queue     : {config.QUEUE_TYPE}")
        print(f"  Queue Host: {config.QUEUE_HOST}:{config.QUEUE_PORT}")
        print(f"  Debug     : {config.DEBUG}")
        print("=" * 60)
        print("\n⚠️  Press Ctrl+C to stop\n")
        
        # Start crawler
        crawler = TikTokLiveCrawler(config)
        crawler.run()
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nUsage:")
        print("  python main.py --username <tiktok_username>")
        print("\nOr set environment variable:")
        print("  export TIKTOK_USERNAME=your_username")
        print("  python main.py")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n✅ Crawler stopped successfully")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()