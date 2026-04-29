.PHONY: build-EventPusherFunction

build-EventPusherFunction:
	pip install -r requirements.txt -t $(ARTIFACTS_DIR) --quiet
	cp -r src/event_pusher $(ARTIFACTS_DIR)/event_pusher