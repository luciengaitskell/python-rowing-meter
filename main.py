PRODUCTION = True

if PRODUCTION is None:
    pass
elif PRODUCTION:
    import run
    run.main()
else:
    try:
        import testing
    except AttributeError: print("NOTHING TO RUN")
    else:
        testing.main()
