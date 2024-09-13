# Messages

GhostOS defines it own Message classes to provide strong type messages, compatible to OpenAI message protocol.

The Message class is capable of a whole message or a streaming package.
In a Message chunks stream, there are:

1. Head package: contains basic information of a message, such as msg_id.
2. Middle packages: chunk of the Message.
3. Tail package: a whole message contains everything of the message, can reset the sending chunks for correction.

And In GhostOS one request may returns multiple messages, 
there are two default protocol message to declare the stream is over:

- final package: notify upstream that all messages are sent.
- error package: notify upstream that all sent messages shall abandon cause an error occurs.