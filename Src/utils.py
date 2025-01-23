def format_time(seconds):
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds:.3f}s"
    elif minutes > 0:
        return f"{minutes}m {seconds:.3f}s"
    else:
        return f"{seconds:.3f}s"
