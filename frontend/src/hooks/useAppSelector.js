import { useDispatch, useSelector } from 'react-redux';

export function useAppDispatch() {
  return useDispatch();
}

export function useAppSelector(selector) {
  return useSelector(selector);
}
