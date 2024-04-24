import React, { useState } from 'react';
import { postText } from './api/postText';
export const Main = () => {
  const [text, setText] = useState('');

  const inputHandler = (e) => {
    setText(e.target.value);
    console.log(text);
  };

  const submitHandler = async (e) => {
    e.preventDefault();
    await postTextHandler();
  };

  const postTextHandler = async () => {
    const res = await postText(text);
    console.log(res);
  };

  return (
    <>
      <form onSubmit={submitHandler}>
        <input
          label='텍스트'
          type='text'
          id='text'
          value={text}
          onChange={(event) => inputHandler(event)}
        ></input>
        <button type='submit'>제출</button>
      </form>
    </>
  );
};
