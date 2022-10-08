./mail_sender consumer --config ./.mailsender.yaml >> ./log_consumer.log 2>&1 &

./mail_sender web --config ./.mailsender.yaml >> ./log_web.log 2>&1 &
