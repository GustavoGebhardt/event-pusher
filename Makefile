.PHONY: build-EventPusherFunction

build-EventPusherFunction:
	uv export --no-dev --no-hashes -o /tmp/event-pusher-deps.txt
	pip install -r /tmp/event-pusher-deps.txt -t $(ARTIFACTS_DIR) --quiet
	cp -r src/event_pusher $(ARTIFACTS_DIR)/event_pusher
